import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import Base, engine
from .routers import admin, public

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Creates any missing tables on boot. For column changes later, add Alembic.
    Base.metadata.create_all(engine)
    yield


settings = get_settings()
app = FastAPI(
    title="Deon API",
    version="1.0.0",
    description="Quotes, invoices, M-Pesa payments (PayHero), receipts and project tracking for deon.ardena.co.ke",
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
    return {"ok": True, "payments": "mock" if settings.payhero_mock else ("live" if settings.payhero_ready else "off")}
