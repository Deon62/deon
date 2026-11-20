from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


def unique_emails(emails) -> list[str]:
    """Drop blanks and repeats (case-insensitive), keep order."""
    seen, out = set(), []
    for e in emails:
        e = str(e or "").strip()
        if "@" in e and e.lower() not in seen:
            seen.add(e.lower())
            out.append(e)
    return out


# Overall project status, separate from the stage it's in.
STATUSES: dict[str, str] = {"active": "Active", "paused": "On hold", "completed": "Completed"}

# Project stages, in order. The tracker shows them as a timeline.
STAGES: dict[str, str] = {
    "discovery": "Discovery",
    "design": "Design",
    "build": "Build",
    "testing": "Testing",
    "launch": "Launch",
    "done": "Complete",
}


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    company: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(40), default="")
    services: Mapped[list] = mapped_column(JSON, default=list)
    extras: Mapped[list] = mapped_column(JSON, default=list)
    timeline: Mapped[str] = mapped_column(String(20), default="standard")
    brief: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="new")  # new, quoted, won, lost
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    client_name: Mapped[str] = mapped_column(String(120))
    client_email: Mapped[str] = mapped_column(String(200), index=True)  # main contact
    # Everyone else on the client's side. They get the same emails and can open /track.
    extra_emails: Mapped[list | None] = mapped_column(JSON, default=list)
    price: Mapped[int | None] = mapped_column(Integer, nullable=True)  # agreed total, if set
    summary: Mapped[str] = mapped_column(Text, default="")
    stage: Mapped[str] = mapped_column(String(20), default="discovery")
    status: Mapped[str] = mapped_column(String(20), default="active", server_default="active")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    quote_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)

    updates: Mapped[list["ProjectUpdate"]] = relationship(
        back_populates="project", order_by="ProjectUpdate.created_at.desc()", cascade="all, delete-orphan"
    )
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="project", order_by="Invoice.created_at")

    @property
    def emails(self) -> list[str]:
        return unique_emails([self.client_email, *(self.extra_emails or [])])

    @property
    def invoiced(self) -> int:
        return sum(i.total for i in self.invoices)

    @property
    def paid(self) -> int:
        return sum(i.paid for i in self.invoices)

    @property
    def balance(self) -> int:
        return sum(i.balance for i in self.invoices)


class ProjectUpdate(Base):
    __tablename__ = "project_updates"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text, default="")
    stage: Mapped[str] = mapped_column(String(20))
    progress: Mapped[int] = mapped_column(Integer)
    link: Mapped[str] = mapped_column(String(300), default="")  # e.g. a staging URL to review
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    project: Mapped[Project] = relationship(back_populates="updates")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    client_name: Mapped[str] = mapped_column(String(120))
    client_company: Mapped[str] = mapped_column(String(120), default="")
    client_email: Mapped[str] = mapped_column(String(200), default="")
    client_phone: Mapped[str] = mapped_column(String(40), default="")
    items: Mapped[list] = mapped_column(JSON, default=list)  # [{desc, qty, rate}]
    subtotal: Mapped[int] = mapped_column(Integer)
    vat: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(Text, default="")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # last payment reminder

    project: Mapped[Project | None] = relationship(back_populates="invoices")
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice")

    @property
    def recipients(self) -> list[str]:
        """The invoice contact plus everyone on its project."""
        return unique_emails([self.client_email, *(self.project.emails if self.project else [])])

    @property
    def lines(self) -> list[dict]:
        return [{"desc": i.get("desc", ""), "amount": round(float(i.get("qty", 1)) * int(i.get("rate", 0)))} for i in self.items or []]

    @property
    def paid(self) -> int:
        return sum(p.amount for p in self.payments if p.status == "success")

    @property
    def balance(self) -> int:
        return max(0, self.total - self.paid)

    @property
    def status(self) -> str:
        if self.balance == 0:
            return "paid"
        return "partly paid" if self.paid else "unpaid"


class Payment(Base):
    """One M-Pesa STK push. A successful payment is also the receipt."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # ours, sent to PayHero
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), nullable=True, index=True)
    amount: Mapped[int] = mapped_column(Integer)
    phone: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending, success, failed
    method: Mapped[str] = mapped_column(String(40), default="M-Pesa", server_default="M-Pesa")  # or Cash, Bank transfer
    message: Mapped[str] = mapped_column(String(300), default="")
    payhero_reference: Mapped[str] = mapped_column(String(64), default="", index=True)
    checkout_request_id: Mapped[str] = mapped_column(String(80), default="", index=True)
    mpesa_code: Mapped[str] = mapped_column(String(32), default="")
    receipt_number: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    receipt_token: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    invoice: Mapped[Invoice | None] = relationship(back_populates="payments")


# Parts of the admin a team member can be given. The owner (ADMIN_KEY) always has all of them, plus Team.
SECTIONS: dict[str, str] = {
    "projects": "Projects",
    "money": "Pending amounts",
    "quotes": "Quotes",
    "payments": "Payments",
    "reminders": "Reminders",
}


class TeamMember(Base):
    """Someone you let into the admin (e.g. a PA) with their own key and only the sections you allow."""

    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), default="")
    access: Mapped[list] = mapped_column(JSON, default=list)  # keys of SECTIONS
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # sha256 of their key
    key_hint: Mapped[str] = mapped_column(String(8), default="")  # last 4 characters, to tell keys apart
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Reminder(Base):
    """A log of reminder emails sent from the admin."""

    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))  # payment, message
    subject: Mapped[str] = mapped_column(String(200))
    recipients: Mapped[list] = mapped_column(JSON, default=list)
    invoice_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    project_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    client_name: Mapped[str] = mapped_column(String(120), default="")
    sent_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
