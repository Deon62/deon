import re
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

# Unambiguous characters for codes people type (no 0/O, 1/I/L).
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def random_code(n: int) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(n))


def next_number(db: Session, column, prefix: str) -> str:
    """Next sequential number like INV-2026-0007 for the given column."""
    year = datetime.now(timezone.utc).year
    stem = f"{prefix}-{year}-"
    latest = db.scalar(select(func.max(column)).where(column.like(stem + "%")))
    n = int(latest.rsplit("-", 1)[1]) + 1 if latest else 1
    return f"{stem}{n:04d}"


def normalise_phone(raw: str) -> str | None:
    """Kenyan mobile number to 2547XXXXXXXX / 2541XXXXXXXX, or None."""
    digits = re.sub(r"\D", "", raw or "")
    m = re.fullmatch(r"(?:254|0)?([17]\d{8})", digits)
    return "254" + m.group(1) if m else None


def mask_phone(phone: str) -> str:
    return phone[:5] + "***" + phone[-3:] if len(phone) >= 9 else phone


class RateLimit:
    """Small in-memory limiter: at most `hits` requests per `window` seconds per client IP.
    Fine for a single Render instance; swap for Redis if you ever scale out."""

    def __init__(self, hits: int, window: int):
        self.hits, self.window = hits, window
        self.log: dict[str, deque[float]] = defaultdict(deque)

    def __call__(self, request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        q, t = self.log[ip], time.monotonic()
        while q and t - q[0] > self.window:
            q.popleft()
        if len(q) >= self.hits:
            raise HTTPException(429, "Too many attempts. Please wait a few minutes and try again.")
        q.append(t)
