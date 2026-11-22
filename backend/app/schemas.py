from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import STAGES, STATUSES

Stage = Literal[tuple(STAGES)]  # type: ignore[valid-type]
Status = Literal[tuple(STATUSES)]  # type: ignore[valid-type]


class Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Quotes ──────────────────────────────────────────────────────────────
class QuoteIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    company: str = Field("", max_length=120)
    email: EmailStr
    phone: str = Field("", max_length=40)
    services: list[str] = Field(min_length=1, max_length=20)
    extras: list[str] = Field(default_factory=list, max_length=20)
    timeline: Literal["flexible", "standard", "rush"] = "standard"
    brief: str = Field("", max_length=5000)


class QuoteOut(Out):
    number: str
    name: str
    company: str
    email: str
    phone: str
    services: list[str]
    extras: list[str]
    timeline: str
    brief: str
    status: str
    created_at: datetime


class QuoteStatusIn(BaseModel):
    status: Literal["new", "quoted", "won", "lost"]


# ── Invoices ────────────────────────────────────────────────────────────
class InvoiceItem(BaseModel):
    desc: str = Field(min_length=1, max_length=200)
    qty: float = Field(gt=0, le=10_000)
    rate: int = Field(ge=0, le=100_000_000)


PayMethod = Literal["Cash", "Bank transfer", "M-Pesa", "Other"]


class InvoiceIn(BaseModel):
    number: str | None = Field(None, max_length=20)  # blank = next INV-YYYY-NNNN
    project_code: str | None = None
    client_name: str = Field(min_length=1, max_length=120)
    client_company: str = Field("", max_length=120)
    client_email: str = Field("", max_length=200)
    client_phone: str = Field("", max_length=40)
    items: list[InvoiceItem] = Field(min_length=1, max_length=50)
    vat: bool = False
    notes: str = Field("", max_length=2000)
    due_days: int = Field(7, ge=0, le=365)
    # Money already received (e.g. a deposit paid before the invoice). Recorded as a payment,
    # so the invoice opens with only the balance pending.
    deposit: int = Field(0, ge=0, le=100_000_000)
    deposit_method: PayMethod = "M-Pesa"
    deposit_reference: str = Field("", max_length=32)
    send_email: bool = True  # email the invoice to the client (and everyone on its project)


class InvoicePublic(Out):
    """What anyone with the invoice number may see: enough to pay it, no contact details."""

    number: str
    lines: list[dict]
    total: int
    paid: int
    balance: int
    status: str
    due_date: date | None


class DefaulterIn(BaseModel):
    defaulter: bool
    note: str = Field("", max_length=300)


class ManualPaymentIn(BaseModel):
    """A payment made outside the site (cash, bank transfer, M-Pesa sent directly)."""

    amount: int = Field(ge=1, le=100_000_000)
    method: PayMethod = "Bank transfer"
    reference: str = Field("", max_length=32)
    send_receipt: bool = True


class InvoiceOut(InvoicePublic):
    client_name: str
    client_company: str
    client_email: str
    client_phone: str
    items: list[dict]
    subtotal: int
    vat: int
    notes: str
    created_at: datetime
    reminded_at: datetime | None = None
    defaulted_at: datetime | None = None
    default_note: str = ""
    defaulter: bool = False
    project_code: str | None = None


# ── Payments ────────────────────────────────────────────────────────────
class PaymentIn(BaseModel):
    phone: str = Field(min_length=9, max_length=20)
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    invoice: str | None = Field(None, max_length=20)
    portion: Literal["full", "deposit"] = "full"  # for invoices
    amount: int | None = Field(None, ge=1, le=250_000)  # for payments without an invoice
    service: str = Field("", max_length=120)


class PaymentStarted(BaseModel):
    reference: str
    amount: int


class PaymentStatus(BaseModel):
    reference: str
    status: str
    amount: int
    message: str = ""
    mpesa_code: str = ""
    receipt_number: str | None = None
    receipt_token: str | None = None


class PaymentOut(Out):
    reference: str
    amount: int
    phone: str
    name: str
    email: str
    description: str
    status: str
    method: str
    message: str
    mpesa_code: str
    receipt_number: str | None
    created_at: datetime
    paid_at: datetime | None


class Receipt(BaseModel):
    number: str
    name: str
    email: str
    phone: str
    amount: int
    description: str
    invoice: str | None
    method: str
    mpesa_code: str
    paid_at: datetime


class ReceiptLookup(BaseModel):
    number: str = Field(min_length=3, max_length=20)
    mpesa_code: str = Field(min_length=4, max_length=32)


# ── Projects ────────────────────────────────────────────────────────────
class ProjectIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    client_name: str = Field(min_length=1, max_length=120)
    client_email: EmailStr
    extra_emails: list[EmailStr] = Field(default_factory=list, max_length=20)
    summary: str = Field("", max_length=3000)
    stage: Stage = "discovery"
    progress: int = Field(0, ge=0, le=100)
    due_date: date | None = None
    quote_number: str | None = None
    # Agreed price. If set, an invoice for it is created, with any deposit already counted.
    price: int | None = Field(None, ge=1, le=100_000_000)
    deposit: int = Field(0, ge=0, le=100_000_000)
    deposit_method: PayMethod = "M-Pesa"
    deposit_reference: str = Field("", max_length=32)
    balance_due_days: int | None = Field(None, ge=0, le=365)  # None = due on the target date
    notify: bool = True  # email the client their tracking code


class ProjectPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=160)
    client_name: str | None = Field(None, min_length=1, max_length=120)
    client_email: EmailStr | None = None
    extra_emails: list[EmailStr] | None = Field(None, max_length=20)
    summary: str | None = Field(None, max_length=3000)
    due_date: date | None = None
    status: Status | None = None
    stage: Stage | None = None
    progress: int | None = Field(None, ge=0, le=100)


class UpdateIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field("", max_length=5000)
    stage: Stage
    progress: int = Field(ge=0, le=100)
    link: str = Field("", max_length=300)
    notify: bool = True  # email the client about this update


class UpdateOut(Out):
    title: str
    body: str
    stage: str
    progress: int
    link: str
    created_at: datetime


class ProjectOut(Out):
    code: str
    title: str
    client_name: str
    client_email: str
    extra_emails: list[str] | None = None
    price: int | None = None
    invoiced: int = 0
    paid: int = 0
    balance: int = 0
    defaulted: bool = False
    summary: str
    stage: str
    status: str
    progress: int
    due_date: date | None
    quote_number: str | None
    created_at: datetime
    updated_at: datetime
    updates: list[UpdateOut]


class TrackIn(BaseModel):
    code: str = Field(min_length=4, max_length=20)
    email: EmailStr


class TrackOut(BaseModel):
    code: str
    title: str
    client_name: str
    summary: str
    stage: str
    status: str
    progress: int
    due_date: date | None
    started: datetime
    updated: datetime
    stages: list[dict]
    updates: list[UpdateOut]
    invoices: list[InvoicePublic]


# ── Team ────────────────────────────────────────────────────────────────
Section = Literal["clients", "projects", "money", "quotes", "payments", "reminders", "emails"]


class TeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field("", max_length=200)
    access: list[Section] = Field(min_length=1)
    send_email: bool = False  # email them their key


class TeamPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=120)
    access: list[Section] | None = Field(None, min_length=1)
    active: bool | None = None


class TeamOut(Out):
    id: int
    name: str
    email: str
    access: list[str]
    key_hint: str
    active: bool
    created_at: datetime
    last_seen_at: datetime | None


# ── Reminders ───────────────────────────────────────────────────────────
class PaymentReminderIn(BaseModel):
    invoices: list[str] = Field(min_length=1, max_length=50)
    note: str = Field("", max_length=2000)


class MessageIn(BaseModel):
    projects: list[str] = Field(min_length=1, max_length=50)
    subject: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=5000)


class EmailIn(BaseModel):
    to: list[EmailStr] = Field(min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=10000)


class EmailPreviewIn(BaseModel):
    name: str = Field("", max_length=120)
    subject: str = Field("", max_length=160)
    message: str = Field("", max_length=10000)


class ReminderOut(Out):
    kind: str
    subject: str
    recipients: list[str]
    invoice_number: str | None
    project_code: str | None
    client_name: str
    sent_by: str
    body: str = ""
    created_at: datetime
