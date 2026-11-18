"""Endpoints the website calls. No login: access is by unguessable codes and tokens."""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .. import payhero
from ..config import get_settings
from ..db import get_db
from ..models import STAGES, Invoice, Payment, Project, Quote
from ..schemas import (
    InvoicePublic,
    PaymentIn,
    PaymentStarted,
    PaymentStatus,
    QuoteIn,
    Receipt,
    ReceiptLookup,
    TrackIn,
    TrackOut,
)
from ..utils import RateLimit, next_number, normalise_phone, random_code

log = logging.getLogger("deon.public")
router = APIRouter(prefix="/api")

quote_limit = RateLimit(hits=5, window=600)
pay_limit = RateLimit(hits=6, window=600)
lookup_limit = RateLimit(hits=20, window=600)

PENDING_TIMEOUT = timedelta(minutes=3)  # an unanswered STK prompt expires well before this
STATUS_CHECK_AFTER = timedelta(seconds=12)  # ask PayHero directly if the callback is slow


def aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ── Quotes ──────────────────────────────────────────────────────────────
@router.post("/quotes", status_code=201, dependencies=[Depends(quote_limit)])
def create_quote(body: QuoteIn, db: Session = Depends(get_db)) -> dict:
    quote = Quote(number=next_number(db, Quote.number, "QT"), **body.model_dump())
    db.add(quote)
    db.commit()
    return {"number": quote.number}


# ── Invoices ────────────────────────────────────────────────────────────
@router.get("/invoices/{number}", response_model=InvoicePublic, dependencies=[Depends(lookup_limit)])
def get_invoice(number: str, db: Session = Depends(get_db)):
    inv = db.scalar(select(Invoice).where(Invoice.number == number.strip().upper()))
    if not inv:
        raise HTTPException(404, "No invoice with that number.")
    return inv


# ── Payments ────────────────────────────────────────────────────────────
@router.post("/payments", response_model=PaymentStarted, status_code=201, dependencies=[Depends(pay_limit)])
async def start_payment(body: PaymentIn, db: Session = Depends(get_db)):
    s = get_settings()
    if not (s.payhero_mock or s.payhero_ready):
        raise HTTPException(503, "Online payments are not switched on yet. Please contact me directly.")

    phone = normalise_phone(body.phone)
    if not phone:
        raise HTTPException(422, "Enter a valid Safaricom number, like 0712 345 678.")

    invoice = None
    if body.invoice:
        invoice = db.scalar(select(Invoice).where(Invoice.number == body.invoice.strip().upper()))
        if not invoice:
            raise HTTPException(404, "No invoice with that number.")
        if invoice.balance <= 0:
            raise HTTPException(409, "This invoice is already paid in full.")
        # The amount comes from the invoice, never from the browser.
        amount = invoice.balance
        if body.portion == "deposit" and invoice.paid == 0:
            amount = min(invoice.balance, round(invoice.total / 2))
        description = f"Invoice {invoice.number}" + (" (50% deposit)" if amount < invoice.balance else "")
    else:
        if not body.amount:
            raise HTTPException(422, "Enter an amount.")
        amount = body.amount
        description = body.service or "Payment"

    if amount > 250_000:
        raise HTTPException(422, "M-Pesa allows up to KES 250,000 per payment. Pay in parts, or contact me.")

    payment = Payment(
        reference="PAY-" + random_code(10),
        invoice=invoice,
        amount=amount,
        phone=phone,
        name=body.name.strip(),
        email=str(body.email),
        description=description[:200],
    )
    db.add(payment)
    db.commit()

    if s.payhero_mock:
        payment.payhero_reference = "MOCK-" + random_code(8)
    else:
        try:
            res = await payhero.stk_push(amount=amount, phone=phone, reference=payment.reference, name=payment.name)
        except payhero.PayHeroError as e:
            payment.status, payment.message = "failed", str(e)
            db.commit()
            raise HTTPException(502, str(e)) from e
        payment.payhero_reference = str(res.get("reference") or "")
        payment.checkout_request_id = str(res.get("CheckoutRequestID") or "")
    db.commit()
    return PaymentStarted(reference=payment.reference, amount=amount)


def mark_success(db: Session, p: Payment, mpesa_code: str) -> None:
    if p.status == "success":
        return
    p.status = "success"
    p.message = ""
    p.mpesa_code = (mpesa_code or "").upper()[:32]
    p.paid_at = datetime.now(timezone.utc)
    p.receipt_number = next_number(db, Payment.receipt_number, "RCT")
    p.receipt_token = secrets.token_urlsafe(18)
    db.commit()
    log.info("payment %s succeeded: KES %s, receipt %s", p.reference, p.amount, p.receipt_number)


def mark_failed(db: Session, p: Payment, message: str) -> None:
    if p.status != "pending":
        return
    p.status = "failed"
    p.message = (message or "The payment was not completed.")[:300]
    db.commit()


@router.get("/payments/{reference}", response_model=PaymentStatus)
async def payment_status(reference: str, db: Session = Depends(get_db)):
    p = db.scalar(select(Payment).where(Payment.reference == reference))
    if not p:
        raise HTTPException(404, "Payment not found.")

    if p.status == "pending":
        age = datetime.now(timezone.utc) - aware(p.created_at)
        if p.payhero_reference.startswith("MOCK-"):
            if age > timedelta(seconds=4):
                mark_success(db, p, "MOCK" + random_code(6))
        elif age > STATUS_CHECK_AFTER and p.payhero_reference:
            # Callback hasn't arrived yet; ask PayHero directly.
            try:
                res = await payhero.transaction_status(p.payhero_reference)
                st = str(res.get("status", "")).upper()
                if st == "SUCCESS":
                    mark_success(db, p, res.get("provider_reference") or res.get("third_party_reference") or "")
                elif st == "FAILED":
                    mark_failed(db, p, "The payment was cancelled or did not go through.")
            except payhero.PayHeroError as e:
                log.warning("status check for %s failed: %s", p.reference, e)
        if p.status == "pending" and age > PENDING_TIMEOUT:
            mark_failed(db, p, "No response from M-Pesa. If money left your account, contact me with the M-Pesa message.")

    return PaymentStatus(
        reference=p.reference, status=p.status, amount=p.amount, message=p.message,
        mpesa_code=p.mpesa_code, receipt_number=p.receipt_number, receipt_token=p.receipt_token,
    )


@router.post("/payhero/callback/{secret}", include_in_schema=False)
async def payhero_callback(secret: str, request: Request, db: Session = Depends(get_db)) -> dict:
    expected = get_settings().payhero_callback_secret
    if not expected or not secrets.compare_digest(secret, expected):
        raise HTTPException(404)
    try:
        data = await request.json()
    except ValueError:
        raise HTTPException(400, "bad json")
    r = data.get("response") if isinstance(data, dict) else None
    if not isinstance(r, dict):
        raise HTTPException(400, "missing response")

    ext, checkout = str(r.get("ExternalReference") or ""), str(r.get("CheckoutRequestID") or "")
    p = db.scalar(select(Payment).where(Payment.reference == ext)) if ext else None
    if not p and checkout:
        p = db.scalar(select(Payment).where(Payment.checkout_request_id == checkout))
    if not p:
        log.warning("callback for unknown payment ext=%s checkout=%s", ext, checkout)
        return {"ok": True}

    ok = str(r.get("ResultCode")) == "0" and str(r.get("Status", "")).lower() == "success"
    paid = int(float(r.get("Amount") or 0))
    if ok and paid == p.amount:
        mark_success(db, p, str(r.get("MpesaReceiptNumber") or ""))
    elif ok:
        log.error("amount mismatch on %s: expected %s got %s", p.reference, p.amount, paid)
        mark_failed(db, p, "Amount mismatch. Please contact me.")
    else:
        mark_failed(db, p, str(r.get("ResultDesc") or "The payment was cancelled."))
    return {"ok": True}


# ── Receipts ────────────────────────────────────────────────────────────
def _receipt(p: Payment) -> Receipt:
    return Receipt(
        number=p.receipt_number or "", name=p.name, email=p.email, phone=p.phone, amount=p.amount,
        description=p.description, invoice=p.invoice.number if p.invoice else None,
        mpesa_code=p.mpesa_code, paid_at=p.paid_at or p.created_at,
    )


@router.get("/receipts/{token}", response_model=Receipt, dependencies=[Depends(lookup_limit)])
def get_receipt(token: str, db: Session = Depends(get_db)):
    p = db.scalar(select(Payment).where(Payment.receipt_token == token, Payment.status == "success"))
    if not p:
        raise HTTPException(404, "Receipt not found.")
    return _receipt(p)


@router.post("/receipts/lookup", dependencies=[Depends(lookup_limit)])
def lookup_receipt(body: ReceiptLookup, db: Session = Depends(get_db)) -> dict:
    p = db.scalar(select(Payment).where(
        Payment.receipt_number == body.number.strip().upper(),
        func.upper(Payment.mpesa_code) == body.mpesa_code.strip().upper(),
        Payment.status == "success",
    ))
    if not p:
        raise HTTPException(404, "No receipt matches that number and M-Pesa code.")
    return {"token": p.receipt_token}


# ── Project tracking ────────────────────────────────────────────────────
@router.post("/track", response_model=TrackOut, dependencies=[Depends(lookup_limit)])
def track(body: TrackIn, db: Session = Depends(get_db)):
    p = db.scalar(
        select(Project)
        .where(Project.code == body.code.strip().upper())
        .options(selectinload(Project.updates), selectinload(Project.invoices).selectinload(Invoice.payments))
    )
    # Same message for "no such code" and "wrong email", so codes can't be probed.
    if not p or p.client_email.strip().lower() != str(body.email).strip().lower():
        raise HTTPException(404, "No project matches that code and email.")

    keys = list(STAGES)
    current = keys.index(p.stage) if p.stage in keys else 0
    stages = [
        {"key": k, "label": STAGES[k], "state": "done" if i < current or p.stage == "done" else "current" if i == current else "next"}
        for i, k in enumerate(keys)
    ]
    return TrackOut(
        code=p.code, title=p.title, client_name=p.client_name, summary=p.summary, stage=p.stage,
        progress=p.progress, due_date=p.due_date, started=p.created_at, updated=p.updated_at,
        stages=stages, updates=p.updates, invoices=p.invoices,
    )
