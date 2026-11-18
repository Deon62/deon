from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (or backend/.env locally)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Render injects DATABASE_URL from the linked Postgres. SQLite is for local runs.
    database_url: str = "sqlite:///./deon.db"

    # Shared secret for /api/admin/* (sent as the X-Admin-Key header). Empty disables admin.
    admin_key: str = ""

    # Comma-separated list of sites allowed to call the API from a browser.
    cors_origins: str = (
        "https://deon.ardena.co.ke,"
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:5511,http://127.0.0.1:5511"
    )

    # Public URL of this API, used to build the PayHero callback URL.
    public_api_url: str = "http://localhost:8000"

    # PayHero (https://payhero.co.ke): API username/password from the dashboard,
    # and the channel id of your M-Pesa till or paybill.
    payhero_api_username: str = ""
    payhero_api_password: str = ""
    payhero_channel_id: int = 0
    payhero_base_url: str = "https://backend.payhero.co.ke/api/v2"
    # Random string placed in the callback path so only PayHero knows the URL.
    payhero_callback_secret: str = ""
    # Simulate successful payments without calling PayHero (local testing only).
    payhero_mock: bool = False

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    @property
    def origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @property
    def payhero_ready(self) -> bool:
        return bool(self.payhero_api_username and self.payhero_api_password and self.payhero_channel_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()
