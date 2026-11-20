"""Endpoints only you and your team use (from /admin and /invoice). Every call needs the X-Admin-Key header:
your ADMIN_KEY (the owner, sees everything) or a team member's own key (only the sections you gave them)."""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .. import emails
from ..config import get_settings
from ..db import get_db
from ..demo import DEMO_CODE, seed_demo
from ..models import SECTIONS, Invoice, Payment, Project, ProjectUpdate, Quote, Reminder, TeamMember
from .public import mark_success
from ..schemas import (
    InvoiceIn,
    ManualPaymentIn,
    InvoiceOut,
    MessageIn,
    PaymentOut,
    PaymentReminderIn,
    ProjectIn,
    ProjectOut,
    ProjectPatch,
    QuoteOut,
    QuoteStatusIn,
    ReminderOut,
    TeamIn,
    TeamOut,
    TeamPatch,
    UpdateIn,
)
from ..utils import RateLimit, next_number, random_code

admin_limit = RateLimit(hits=120, window=60)


@dataclass
class Actor:
    name: str
    owner: bool
    access: set[str] = field(default_factory=set)

    def can(self, section: str) -> bool:
        return self.owner or section in self.access


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _needs(path: str, method: str) -> set[str] | None:
    """Which sections may call this path. None = anyone signed in. Empty set = owner only."""
    part = path.removeprefix("/api/admin").strip("/").split("/")[0]
    if part in ("check", "overview"):
        return None
    if part == "projects" and method == "GET":
        return {"projects", "money", "reminders"}  # the money and reminder forms list projects
    if part in ("projects", "demo"):
        return {"projects"}
    if part == "invoices":
        return {"money"}
    if part in ("quotes", "payments", "reminders"):
        return {part}
    return set()  # team, email-test


def require_admin(request: Request, x_admin_key: str = Header(""), db: Session = Depends(get_db)) -> Actor:
    s = get_settings()
    if not s.admin_key:
        raise HTTPException(503, "Admin is disabled: set ADMIN_KEY on the server.")
    if x_admin_key and secrets.compare_digest(x_admin_key, s.admin_key):
        actor = Actor(name="Deon", owner=True, access=set(SECTIONS))
    else:
        m = db.scalar(select(TeamMember).where(TeamMember.key_hash == hash_key(x_admin_key))) if x_admin_key else None
        if not m or not m.active:
            raise HTTPException(401, "Wrong admin key.")
        if not m.last_seen_at or datetime.now(timezone.utc) - _aware(m.last_seen_at) > timedelta(minutes=5):
            m.last_seen_at = datetime.now(timezone.utc)
            db.commit()
        actor = Actor(name=m.name, owner=False, access=set(m.access or []))
    need = _needs(request.url.path, request.method)
    if need is not None and not actor.owner and not (need & actor.access):
        raise HTTPException(403, "You don't have access to this. Ask Deon to add it.")
    request.state.actor = actor
    return actor


def _aware(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


router = APIRouter(prefix="/api/admin", dependencies=[Depends(admin_limit), Depends(require_admin)])


@router.get("/check")
def check(request: Request) -> dict:
    a: Actor = request.state.actor
    return {"ok": True, "email": emails.enabled(), "name": a.name, "owner": a.owner,
            "access": sorted(a.access), "sections": SECTIONS}


@router.post("/email-test")
async def email_test() -> dict:
    """Sends a sample of each client email to NOTIFY_EMAIL so you can see them."""
    s = get_settings()
    if not emails.enabled():
        raise HTTPException(503, "Emails are off: set RESEND_API_KEY on the server.")
    today = date.today()
    project = {"code": "DO-DEMO01", "title": "Bloom Cafe website & ordering", "client_name": "Deon Orina",
               "client_email": s.notify_email, "due_date": today + timedelta(days=21)}
    samples = [
        emails.quote_received({"number": "QT-2026-0000", "name": "Deon Orina", "services": ["website", "payments"],
                               "extras": ["mpesa", "seo"], "timeline": "standard"}),
        emails.project_welcome({**project, "emails": [s.notify_email, "team@example.com"]},
                               {"invoice": "INV-2026-0000", "total": 120000, "paid": 60000, "balance": 60000,
                                "due_date": today + timedelta(days=21), "receipt_token": None}),
        emails.project_update(project, {"title": "Homepage design ready for review", "stage": "design", "progress": 35,
                                        "body": "Desktop and mobile layouts are up. Leave comments on anything you'd change.",
                                        "link": s.site_url}),
        emails.invoice_issued({"number": "INV-2026-0000", "client_name": "Deon Orina", "created_at": today,
                               "due_date": today + timedelta(days=7), "items": [{"desc": "Website design & build", "qty": 1, "rate": 90000},
                               {"desc": "M-Pesa checkout", "qty": 1, "rate": 30000}], "vat": 0, "total": 120000,
                               "notes": "50% deposit to start, balance on delivery.", "project_code": "DO-DEMO01",
                               "paid": 60000, "balance": 60000}),
    ]
    sent = 0
    for subject, html, text in samples:
        sent += await emails.send(s.notify_email, "[Test] " + subject, html, text)
    if not sent:
        raise HTTPException(502, "Resend rejected the emails. Check the server logs and that your domain is verified.")
    return {"sent": sent, "to": s.notify_email}


# ── Overview ────────────────────────────────────────────────────────
@router.get("/overview")
def overview(request: Request, db: Session = Depends(get_db)) -> dict:
    """Everything the Overview page shows. Parts a team member can't open are left out. The sample project isn't counted."""
    a: Actor = request.state.actor
    today = date.today()
    out: dict = {"name": a.name}

    if a.can("money") or a.can("payments"):
        invoices = db.scalars(select(Invoice).options(selectinload(Invoice.payments), selectinload(Invoice.project))).all()
        outstanding = sorted((i for i in invoices if i.balance > 0), key=lambda i: (i.due_date or date.max, i.created_at))
        paid = db.scalars(select(Payment).where(Payment.status == "success").order_by(Payment.paid_at.desc())).all()
        # Collected per month for the last 6 months, oldest first.
        months = []
        y, m = today.year, today.month
        for _ in range(6):
            months.append((y, m))
            y, m = (y - 1, 12) if m == 1 else (y, m - 1)
        months.reverse()
        series = [{"month": f"{y}-{m:02d}", "amount": sum(p.amount for p in paid if p.paid_at and (p.paid_at.year, p.paid_at.month) == (y, m))}
                  for y, m in months]
        out.update({
            "outstanding_total": sum(i.balance for i in outstanding),
            "outstanding_count": len(outstanding),
            "overdue_total": sum(i.balance for i in outstanding if i.due_date and i.due_date < today),
            "overdue_count": sum(1 for i in outstanding if i.due_date and i.due_date < today),
            "collected_month": series[-1]["amount"],
            "collected_last_month": series[-2]["amount"],
            "collected_total": sum(p.amount for p in paid),
            "monthly": series,
            "outstanding": [_invoice_out(i).model_dump(mode="json") for i in outstanding[:6]],
            "recent_payments": [PaymentOut.model_validate(p).model_dump(mode="json") for p in paid[:6]],
        })

    if a.can("projects") or a.can("money") or a.can("reminders"):
        projects = db.scalars(select(Project).where(Project.code != DEMO_CODE).order_by(Project.updated_at.desc())).all()
        live = [p for p in projects if p.status != "completed"]
        out.update({
            "projects": {s: sum(1 for p in projects if p.status == s) for s in ("active", "paused", "completed")},
            "stages": {s: sum(1 for p in live if p.stage == s) for s in ("discovery", "design", "build", "testing", "launch")},
            "projects_recent": [
                {"code": p.code, "title": p.title, "client_name": p.client_name, "status": p.status,
                 "stage": p.stage, "progress": p.progress, "due_date": p.due_date.isoformat() if p.due_date else None,
                 "updated_at": p.updated_at.isoformat()}
                for p in live
            ][:6],
        })

    if a.can("quotes"):
        out["quotes_new"] = len(db.scalars(select(Quote.id).where(Quote.status == "new")).all())

    # One feed of what happened lately, newest first.
    feed = []
    if a.can("payments") or a.can("money"):
        feed += [{"kind": "payment", "at": p["paid_at"] or p["created_at"], "title": f"{p['name']} paid", "detail": p["description"],
                  "amount": p["amount"]} for p in out.get("recent_payments", [])]
    if a.can("projects"):
        ups = db.scalars(select(ProjectUpdate).join(Project).where(Project.code != DEMO_CODE)
                         .options(selectinload(ProjectUpdate.project)).order_by(ProjectUpdate.created_at.desc()).limit(6)).all()
        feed += [{"kind": "update", "at": _aware(u.created_at).isoformat(), "title": u.title, "detail": u.project.title} for u in ups]
    if a.can("quotes"):
        qs = db.scalars(select(Quote).order_by(Quote.created_at.desc()).limit(4)).all()
        feed += [{"kind": "quote", "at": _aware(q.created_at).isoformat(), "title": f"Quote request from {q.name}",
                  "detail": q.company or q.email} for q in qs]
    if a.can("reminders"):
        rs = db.scalars(select(Reminder).order_by(Reminder.created_at.desc()).limit(4)).all()
        feed += [{"kind": "reminder", "at": _aware(r.created_at).isoformat(), "title": f"Reminder to {r.client_name}",
                  "detail": r.subject} for r in rs]
    out["activity"] = sorted(feed, key=lambda f: f["at"], reverse=True)[:8]
    return out


# ── Quotes ──────────────────────────────────────────────────────────────
@router.get("/quotes", response_model=list[QuoteOut])
def list_quotes(db: Session = Depends(get_db)):
    return db.scalars(select(Quote).order_by(Quote.created_at.desc()).limit(200)).all()


@router.patch("/quotes/{number}", response_model=QuoteOut)
def set_quote_status(number: str, body: QuoteStatusIn, db: Session = Depends(get_db)):
    q = db.scalar(select(Quote).where(Quote.number == number.upper()))
    if not q:
        raise HTTPException(404, "Quote not found.")
    q.status = body.status
    db.commit()
    return q


# ── Invoices ────────────────────────────────────────────────────────────
def _invoice_out(inv: Invoice) -> InvoiceOut:
    out = InvoiceOut.model_validate(inv)
    out.project_code = inv.project.code if inv.project else None
    return out


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Invoice).options(selectinload(Invoice.payments), selectinload(Invoice.project))
        .order_by(Invoice.created_at.desc()).limit(200)
    ).all()
    return [_invoice_out(i) for i in rows]


@router.get("/invoices/next-number")
def next_invoice_number(db: Session = Depends(get_db)) -> dict:
    return {"number": next_number(db, Invoice.number, "INV")}


def _invoice_email(inv: Invoice) -> dict:
    return {"number": inv.number, "client_name": inv.client_name, "created_at": inv.created_at, "due_date": inv.due_date,
            "items": inv.items, "vat": inv.vat, "total": inv.total, "paid": inv.paid, "balance": inv.balance,
            "notes": inv.notes, "project_code": inv.project.code if inv.project else None}


def _record(db: Session, inv: Invoice, amount: int, method: str, reference: str, bg: BackgroundTasks, *,
            label: str = "part payment", email_client: bool = True, notify_admin: bool = True) -> Payment:
    """Record money received outside the site against an invoice, as a paid payment with a receipt."""
    if amount > inv.balance:
        raise HTTPException(422, f"That's more than the pending amount ({inv.balance:,}).")
    p = Payment(
        reference="PAY-" + random_code(10), invoice=inv, amount=amount, phone="", method=method,
        name=inv.client_name, email=inv.client_email or "", status="pending",
        description=f"Invoice {inv.number}" + (f" ({label})" if amount < inv.balance else ""),
    )
    db.add(p)
    db.commit()
    mark_success(db, p, reference or method.upper().replace(" ", "-"), bg, email_client=email_client, notify_admin=notify_admin)
    db.refresh(inv)
    return p


def _new_invoice(db: Session, *, project: Project | None, client_name: str, client_email: str, items: list[dict],
                 vat: bool = False, due_date: date | None = None, number: str | None = None, **extra) -> Invoice:
    number = (number or "").strip().upper() or next_number(db, Invoice.number, "INV")
    if db.scalar(select(Invoice.id).where(Invoice.number == number)):
        raise HTTPException(409, f"Invoice {number} already exists.")
    subtotal = round(sum(i["qty"] * i["rate"] for i in items))
    tax = round(subtotal * 0.16) if vat else 0
    inv = Invoice(number=number, project=project, client_name=client_name, client_email=client_email, items=items,
                  subtotal=subtotal, vat=tax, total=subtotal + tax, due_date=due_date, **extra)
    db.add(inv)
    db.commit()
    return inv


@router.post("/invoices", response_model=InvoiceOut, status_code=201)
def create_invoice(body: InvoiceIn, bg: BackgroundTasks, db: Session = Depends(get_db)):
    project = None
    if body.project_code:
        project = db.scalar(select(Project).where(Project.code == body.project_code.strip().upper()))
        if not project:
            raise HTTPException(404, "No project with that code.")
    items = [{"desc": i.desc, "qty": i.qty, "rate": i.rate} for i in body.items]
    total = round(sum(i["qty"] * i["rate"] for i in items) * (1.16 if body.vat else 1))
    if body.deposit >= total:
        raise HTTPException(422, "The amount already received must be less than the total.")
    inv = _new_invoice(
        db, project=project, number=body.number, client_name=body.client_name, client_email=body.client_email,
        items=items, vat=body.vat, due_date=date.today() + timedelta(days=body.due_days) if body.due_days else None,
        client_company=body.client_company, client_phone=body.client_phone, notes=body.notes,
    )
    if body.deposit:
        _record(db, inv, body.deposit, body.deposit_method, body.deposit_reference, bg,
                label="deposit", email_client=False, notify_admin=False)
    if body.send_email and inv.recipients:
        bg.add_task(emails.send, inv.recipients, *emails.invoice_issued(_invoice_email(inv)))
    return _invoice_out(inv)


@router.post("/invoices/{number}/send")
def send_invoice(number: str, bg: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    """Email the invoice as it stands now (what's been paid and what's left), e.g. as a reminder."""
    inv = db.scalar(select(Invoice).where(Invoice.number == number.upper())
                    .options(selectinload(Invoice.payments), selectinload(Invoice.project)))
    if not inv:
        raise HTTPException(404, "Invoice not found.")
    if not inv.balance:
        raise HTTPException(409, "This invoice is paid in full.")
    if not inv.recipients:
        raise HTTPException(422, "This invoice has no email address. Add one to its project first.")
    bg.add_task(emails.send, inv.recipients, *emails.invoice_issued(_invoice_email(inv)))
    return {"to": inv.recipients}


@router.post("/invoices/{number}/payments", response_model=InvoiceOut, status_code=201)
def record_payment(number: str, body: ManualPaymentIn, bg: BackgroundTasks, db: Session = Depends(get_db)):
    """Record money received outside the site, so the pending amount and receipts stay right."""
    inv = db.scalar(select(Invoice).where(Invoice.number == number.upper()).options(selectinload(Invoice.payments)))
    if not inv:
        raise HTTPException(404, "Invoice not found.")
    _record(db, inv, body.amount, body.method, body.reference, bg, email_client=body.send_receipt)
    return _invoice_out(inv)


@router.delete("/invoices/{number}", status_code=204)
def delete_invoice(number: str, db: Session = Depends(get_db)) -> None:
    inv = db.scalar(select(Invoice).where(Invoice.number == number.upper()).options(selectinload(Invoice.payments)))
    if not inv:
        raise HTTPException(404, "Invoice not found.")
    if inv.paid:
        raise HTTPException(409, "This invoice has payments against it, so it can't be deleted.")
    for p in inv.payments:
        p.invoice_id = None
    db.delete(inv)
    db.commit()


# ── Payments ────────────────────────────────────────────────────────────
@router.get("/payments", response_model=list[PaymentOut])
def list_payments(db: Session = Depends(get_db)):
    return db.scalars(select(Payment).order_by(Payment.created_at.desc()).limit(200)).all()


# ── Projects ────────────────────────────────────────────────────────────
_PROJECT_LOAD = (selectinload(Project.updates), selectinload(Project.invoices).selectinload(Invoice.payments))


def _get_project(db: Session, code: str) -> Project:
    p = db.scalar(select(Project).where(Project.code == code.upper()).options(*_PROJECT_LOAD))
    if not p:
        raise HTTPException(404, "Project not found.")
    return p


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.scalars(
        select(Project).options(*_PROJECT_LOAD).order_by(Project.updated_at.desc())
    ).all()


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, bg: BackgroundTasks, db: Session = Depends(get_db)):
    if body.price and body.deposit >= body.price:
        raise HTTPException(422, "The deposit must be less than the agreed price.")
    if body.deposit and not body.price:
        raise HTTPException(422, "Enter the agreed price so the deposit can be counted against it.")
    code = "DO-" + random_code(6)
    while db.scalar(select(Project.id).where(Project.code == code)):
        code = "DO-" + random_code(6)
    p = Project(code=code, **body.model_dump(include={"title", "client_name", "summary", "stage", "progress",
                                                      "due_date", "quote_number", "price"}))
    p.client_email = str(body.client_email)
    p.extra_emails = [str(e) for e in body.extra_emails]
    p.extra_emails = p.emails[1:]  # drops blanks and repeats of the main email
    p.updates.append(ProjectUpdate(
        title="Project started", body=body.summary, stage=body.stage, progress=body.progress,
    ))
    if body.quote_number:
        q = db.scalar(select(Quote).where(Quote.number == body.quote_number.upper()))
        if q:
            q.status = "won"
    db.add(p)
    db.commit()

    money = None
    if body.price:
        # One invoice for the whole price. The deposit is recorded against it, so only the balance is pending.
        due = date.today() + timedelta(days=body.balance_due_days) if body.balance_due_days is not None else body.due_date
        inv = _new_invoice(db, project=p, client_name=p.client_name, client_email=p.client_email,
                           items=[{"desc": p.title, "qty": 1, "rate": body.price}], due_date=due)
        receipt = None
        if body.deposit:
            receipt = _record(db, inv, body.deposit, body.deposit_method, body.deposit_reference, bg,
                              label="deposit", email_client=False, notify_admin=False)
        money = {"invoice": inv.number, "total": inv.total, "paid": inv.paid, "balance": inv.balance, "due_date": inv.due_date,
                 "receipt_token": receipt.receipt_token if receipt else None}
    if body.notify:
        bg.add_task(emails.send, p.emails, *emails.project_welcome(_project_dict(p), money))
    return _get_project(db, p.code)


def _project_dict(p: Project) -> dict:
    return {"code": p.code, "title": p.title, "client_name": p.client_name, "client_email": p.client_email,
            "emails": p.emails, "due_date": p.due_date}


@router.patch("/projects/{code}", response_model=ProjectOut)
def edit_project(code: str, body: ProjectPatch, db: Session = Depends(get_db)):
    p = _get_project(db, code)
    for k, v in body.model_dump(exclude_unset=True).items():
        if k == "client_email" and v:
            v = str(v)
        elif k == "extra_emails":
            v = [str(e) for e in v or []]
        setattr(p, k, v)
    p.extra_emails = [e for e in p.emails if e.lower() != p.client_email.lower()]
    if body.status == "completed":
        p.stage, p.progress = "done", 100
    db.commit()
    return p


@router.post("/projects/{code}/updates", response_model=ProjectOut, status_code=201)
def post_update(code: str, body: UpdateIn, bg: BackgroundTasks, db: Session = Depends(get_db)):
    """Post progress. Moves the project to the update's stage and percentage."""
    p = _get_project(db, code)
    p.updates.append(ProjectUpdate(**body.model_dump(exclude={"notify"})))
    p.stage, p.progress = body.stage, body.progress
    if body.stage == "done":
        p.status = "completed"
    elif p.status == "completed":
        p.status = "active"
    db.commit()
    if body.notify:
        bg.add_task(emails.send, p.emails, *emails.project_update(_project_dict(p), body.model_dump()))
    db.refresh(p)
    return p


@router.post("/demo/reset", status_code=204)
def reset_demo() -> None:
    """Rebuild the sample project with fresh dates and its full update history."""
    seed_demo(reset=True)


@router.delete("/projects/{code}", status_code=204)
def delete_project(code: str, db: Session = Depends(get_db)) -> None:
    """Deletes the project and its updates. Its invoices and payments are kept, just no longer linked to it."""
    p = _get_project(db, code)
    for inv in db.scalars(select(Invoice).where(Invoice.project_id == p.id)):
        inv.project_id = None
    db.delete(p)
    db.commit()


# ── Reminders ───────────────────────────────────────────────────────────
@router.get("/reminders", response_model=list[ReminderOut])
def list_reminders(db: Session = Depends(get_db)):
    return db.scalars(select(Reminder).order_by(Reminder.created_at.desc()).limit(100)).all()


@router.post("/reminders/payments")
def send_payment_reminders(body: PaymentReminderIn, request: Request, bg: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    """Email a payment reminder for each invoice (to its contact and everyone on its project)."""
    who = request.state.actor.name
    numbers = {n.strip().upper() for n in body.invoices}
    rows = db.scalars(select(Invoice).where(Invoice.number.in_(numbers))
                      .options(selectinload(Invoice.payments), selectinload(Invoice.project))).all()
    sent, skipped = [], []
    for inv in rows:
        if not inv.balance or not inv.recipients:
            skipped.append(inv.number)
            continue
        data = _invoice_email(inv)
        subject, html, text = emails.payment_reminder(data, body.note.strip())
        bg.add_task(emails.send, inv.recipients, subject, html, text)
        inv.reminded_at = datetime.now(timezone.utc)
        db.add(Reminder(kind="payment", subject=subject, recipients=inv.recipients, invoice_number=inv.number,
                        project_code=data["project_code"], client_name=inv.client_name, sent_by=who))
        sent.append(inv.number)
    db.commit()
    skipped += sorted(numbers - {i.number for i in rows})
    return {"sent": sent, "skipped": skipped}


@router.post("/reminders/messages")
def send_messages(body: MessageIn, request: Request, bg: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    """Email your own message to everyone on each chosen project."""
    who = request.state.actor.name
    codes = {c.strip().upper() for c in body.projects}
    rows = db.scalars(select(Project).where(Project.code.in_(codes), Project.code != DEMO_CODE)).all()
    sent = []
    for p in rows:
        subject, html, text = emails.client_message(_project_dict(p), body.subject.strip(), body.message)
        bg.add_task(emails.send, p.emails, subject, html, text)
        db.add(Reminder(kind="message", subject=subject, recipients=p.emails, project_code=p.code,
                        client_name=p.client_name, sent_by=who))
        sent.append(p.code)
    db.commit()
    return {"sent": sent, "skipped": sorted(codes - set(sent))}


# ── Team (owner only) ───────────────────────────────────────────────────
def _new_key() -> str:
    return "tm_" + secrets.token_urlsafe(24)


def _get_member(db: Session, member_id: int) -> TeamMember:
    m = db.get(TeamMember, member_id)
    if not m:
        raise HTTPException(404, "Team member not found.")
    return m


@router.get("/team", response_model=list[TeamOut])
def list_team(db: Session = Depends(get_db)):
    return db.scalars(select(TeamMember).order_by(TeamMember.created_at)).all()


@router.post("/team", status_code=201)
def add_member(body: TeamIn, bg: BackgroundTasks, db: Session = Depends(get_db)) -> dict:
    """Returns their key once. Only a hash is stored, so it can't be shown again (reset it instead)."""
    key = _new_key()
    m = TeamMember(name=body.name.strip(), email=body.email.strip(), access=sorted(set(body.access)),
                   key_hash=hash_key(key), key_hint=key[-4:])
    db.add(m)
    db.commit()
    if body.send_email and "@" in m.email:
        bg.add_task(emails.send, m.email, *emails.team_invite(m.name, key, [SECTIONS[x] for x in m.access]))
    return {"member": TeamOut.model_validate(m).model_dump(mode="json"), "key": key}


@router.patch("/team/{member_id}", response_model=TeamOut)
def edit_member(member_id: int, body: TeamPatch, db: Session = Depends(get_db)):
    m = _get_member(db, member_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(m, k, sorted(set(v)) if k == "access" else v)
    db.commit()
    return m


@router.post("/team/{member_id}/key")
def reset_member_key(member_id: int, db: Session = Depends(get_db)) -> dict:
    """New key for them. The old one stops working at once."""
    m = _get_member(db, member_id)
    key = _new_key()
    m.key_hash, m.key_hint = hash_key(key), key[-4:]
    db.commit()
    return {"key": key}


@router.delete("/team/{member_id}", status_code=204)
def remove_member(member_id: int, db: Session = Depends(get_db)) -> None:
    db.delete(_get_member(db, member_id))
    db.commit()
