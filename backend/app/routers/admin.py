"""Endpoints only you use (from /admin and /invoice). Every call needs the X-Admin-Key header."""

import secrets
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import get_settings
from ..db import get_db
from ..models import Invoice, Payment, Project, ProjectUpdate, Quote
from ..schemas import (
    InvoiceIn,
    InvoiceOut,
    PaymentOut,
    ProjectIn,
    ProjectOut,
    ProjectPatch,
    QuoteOut,
    QuoteStatusIn,
    UpdateIn,
)
from ..utils import RateLimit, next_number, random_code

admin_limit = RateLimit(hits=120, window=60)


def require_admin(x_admin_key: str = Header("")) -> None:
    key = get_settings().admin_key
    if not key:
        raise HTTPException(503, "Admin is disabled: set ADMIN_KEY on the server.")
    if not secrets.compare_digest(x_admin_key, key):
        raise HTTPException(401, "Wrong admin key.")


router = APIRouter(prefix="/api/admin", dependencies=[Depends(admin_limit), Depends(require_admin)])


@router.get("/check")
def check() -> dict:
    return {"ok": True}


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


@router.post("/invoices", response_model=InvoiceOut, status_code=201)
def create_invoice(body: InvoiceIn, db: Session = Depends(get_db)):
    number = (body.number or "").strip().upper() or next_number(db, Invoice.number, "INV")
    if db.scalar(select(Invoice.id).where(Invoice.number == number)):
        raise HTTPException(409, f"Invoice {number} already exists.")
    project = None
    if body.project_code:
        project = db.scalar(select(Project).where(Project.code == body.project_code.strip().upper()))
        if not project:
            raise HTTPException(404, "No project with that code.")

    items = [{"desc": i.desc, "qty": i.qty, "rate": i.rate} for i in body.items]
    subtotal = round(sum(i["qty"] * i["rate"] for i in items))
    vat = round(subtotal * 0.16) if body.vat else 0
    inv = Invoice(
        number=number, project=project, client_name=body.client_name, client_company=body.client_company,
        client_email=body.client_email, client_phone=body.client_phone, items=items,
        subtotal=subtotal, vat=vat, total=subtotal + vat, notes=body.notes,
        due_date=date.today() + timedelta(days=body.due_days) if body.due_days else None,
    )
    db.add(inv)
    db.commit()
    return _invoice_out(inv)


# ── Payments ────────────────────────────────────────────────────────────
@router.get("/payments", response_model=list[PaymentOut])
def list_payments(db: Session = Depends(get_db)):
    return db.scalars(select(Payment).order_by(Payment.created_at.desc()).limit(200)).all()


# ── Projects ────────────────────────────────────────────────────────────
def _get_project(db: Session, code: str) -> Project:
    p = db.scalar(select(Project).where(Project.code == code.upper()).options(selectinload(Project.updates)))
    if not p:
        raise HTTPException(404, "Project not found.")
    return p


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.scalars(
        select(Project).options(selectinload(Project.updates)).order_by(Project.updated_at.desc())
    ).all()


@router.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectIn, db: Session = Depends(get_db)):
    code = "DO-" + random_code(6)
    while db.scalar(select(Project.id).where(Project.code == code)):
        code = "DO-" + random_code(6)
    p = Project(code=code, **body.model_dump())
    p.updates.append(ProjectUpdate(
        title="Project started", body=body.summary, stage=body.stage, progress=body.progress,
    ))
    if body.quote_number:
        q = db.scalar(select(Quote).where(Quote.number == body.quote_number.upper()))
        if q:
            q.status = "won"
    db.add(p)
    db.commit()
    return p


@router.patch("/projects/{code}", response_model=ProjectOut)
def edit_project(code: str, body: ProjectPatch, db: Session = Depends(get_db)):
    p = _get_project(db, code)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    return p


@router.post("/projects/{code}/updates", response_model=ProjectOut, status_code=201)
def post_update(code: str, body: UpdateIn, db: Session = Depends(get_db)):
    """Post progress. Moves the project to the update's stage and percentage."""
    p = _get_project(db, code)
    p.updates.append(ProjectUpdate(**body.model_dump()))
    p.stage, p.progress = body.stage, body.progress
    db.commit()
    db.refresh(p)
    return p


@router.delete("/projects/{code}", status_code=204)
def delete_project(code: str, db: Session = Depends(get_db)) -> None:
    p = _get_project(db, code)
    for inv in db.scalars(select(Invoice).where(Invoice.project_id == p.id)):
        inv.project_id = None
    db.delete(p)
    db.commit()
