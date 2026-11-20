"""The sample project anyone can open on /track with code DO-DEMO01 and demo@deon.ardena.co.ke."""

import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from .db import SessionLocal
from .models import Invoice, Project, ProjectUpdate

log = logging.getLogger("deon")

DEMO_CODE, DEMO_EMAIL = "DO-DEMO01", "demo@deon.ardena.co.ke"

HISTORY = [
    (18, "Project started", "Kickoff call done. Pages, features and timeline agreed.", "discovery", 5, ""),
    (14, "Sitemap and content plan approved", "Five pages: Home, Menu, Order, About, Contact.", "discovery", 15, ""),
    (9, "Homepage and menu designs ready", "Desktop and mobile layouts for review. Comments welcome.", "design", 35, "https://deon.ardena.co.ke"),
    (2, "Ordering flow built", "Cart, M-Pesa checkout and order emails are working on staging. Admin for prices is next.", "build", 60, ""),
]


def seed_demo(reset: bool = False) -> None:
    """Create the sample project if it's missing. reset=True rebuilds it with fresh dates and its full history.
    It has no invoices, so nothing on it can be paid."""
    with SessionLocal() as db:
        old = db.scalar(select(Project).where(Project.code == DEMO_CODE))
        if old and not reset:
            return
        if old:
            for inv in db.scalars(select(Invoice).where(Invoice.project_id == old.id)):
                inv.project_id = None
            db.delete(old)
            db.flush()
        now = datetime.now(timezone.utc)
        p = Project(
            code=DEMO_CODE, title="Bloom Cafe website & ordering", client_name="Demo Client", client_email=DEMO_EMAIL,
            summary="A fast, mobile-first website for a Nairobi cafe, with an online menu, M-Pesa ordering and an admin to update prices.",
            stage="build", status="active", progress=60, due_date=date.today() + timedelta(days=21),
        )
        for days, title, body, stage, pct, link in HISTORY:
            p.updates.append(ProjectUpdate(title=title, body=body, stage=stage, progress=pct, link=link,
                                           created_at=now - timedelta(days=days)))
        db.add(p)
        db.commit()
        log.info("%s demo project %s", "reset" if old else "seeded", DEMO_CODE)
