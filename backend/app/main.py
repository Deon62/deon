import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, select, text

from . import emails
from .config import get_settings
from .db import Base, SessionLocal, engine
from .models import Project, ProjectUpdate
from .routers import admin, public

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("deon")

DEMO_CODE, DEMO_EMAIL = "DO-DEMO01", "demo@deon.ardena.co.ke"


def add_missing_columns() -> None:
    """create_all() makes new tables but never alters old ones. Add columns introduced later."""
    wanted = {
        "projects": {"status": "VARCHAR(20) NOT NULL DEFAULT 'active'"},
        "payments": {"method": "VARCHAR(40) NOT NULL DEFAULT 'M-Pesa'"},
    }
    insp = inspect(engine)
    with engine.begin() as conn:
        for table, cols in wanted.items():
            if not insp.has_table(table):
                continue
            have = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols.items():
                if name not in have:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                    log.info("added column %s.%s", table, name)


def seed_demo() -> None:
    """A sample project anyone can open on /track with code DO-DEMO01 and demo@deon.ardena.co.ke.
    No invoices, so nothing on it can be paid."""
    with SessionLocal() as db:
        if db.scalar(select(Project.id).where(Project.code == DEMO_CODE)):
            return
        now = datetime.now(timezone.utc)
        p = Project(
            code=DEMO_CODE, title="Bloom Cafe website & ordering", client_name="Demo Client", client_email=DEMO_EMAIL,
            summary="A fast, mobile-first website for a Nairobi cafe, with an online menu, M-Pesa ordering and an admin to update prices.",
            stage="build", status="active", progress=60, due_date=date.today() + timedelta(days=21),
        )
        history = [
            (18, "Project started", "Kickoff call done. Pages, features and timeline agreed.", "discovery", 5, ""),
            (14, "Sitemap and content plan approved", "Five pages: Home, Menu, Order, About, Contact.", "discovery", 15, ""),
            (9, "Homepage and menu designs ready", "Desktop and mobile layouts for review. Comments welcome.", "design", 35, "https://deon.ardena.co.ke"),
            (2, "Ordering flow built", "Cart, M-Pesa checkout and order emails are working on staging. Admin for prices is next.", "build", 60, ""),
        ]
        for days, title, body, stage, pct, link in history:
            p.updates.append(ProjectUpdate(title=title, body=body, stage=stage, progress=pct, link=link,
                                           created_at=now - timedelta(days=days)))
        db.add(p)
        db.commit()
        log.info("seeded demo project %s", DEMO_CODE)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    add_missing_columns()
    if get_settings().seed_demo:
        seed_demo()
    yield


settings = get_settings()
app = FastAPI(
    title="Deon API",
    version="1.1.0",
    description="Quotes, invoices, M-Pesa payments (PayHero), receipts, project tracking and email for deon.ardena.co.ke",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-Admin-Key"],
    max_age=600,
)

app.include_router(public.router)
app.include_router(admin.router)


@app.get("/", include_in_schema=False)
@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {
        "ok": True,
        "payments": "mock" if settings.payhero_mock else ("live" if settings.payhero_ready else "off"),
        "email": "on" if emails.enabled() else "off",
        "database": "postgres" if settings.sqlalchemy_url.startswith("postgresql") else "sqlite",
    }
