import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from . import emails
from .config import get_settings
from .db import Base, engine
from .demo import seed_demo
from .routers import admin, public

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("deon")


def add_missing_columns() -> None:
    """create_all() makes new tables but never alters old ones. Add columns introduced later."""
    wanted = {
        "projects": {
            "status": "VARCHAR(20) NOT NULL DEFAULT 'active'",
            "extra_emails": "JSON",
            "price": "INTEGER",
        },
        "payments": {"method": "VARCHAR(40) NOT NULL DEFAULT 'M-Pesa'"},
        "invoices": {"reminded_at": "TIMESTAMP WITH TIME ZONE"},
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
