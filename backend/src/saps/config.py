"""Settings read from environment variables (Developer Guide §6)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration of the SAPS API and SAPS Worker."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # SAPS Database (ADR-0003, ADR-0005)
    database_url: str = "postgresql+psycopg://saps:saps@localhost:5432/saps"

    # SAPS Message Broker and SAPS Worker (ADR-0004)
    redis_url: str = "redis://localhost:6379/0"
    dramatiq_heartbeat_timeout_ms: int = Field(default=30_000, gt=0)
    dramatiq_maintenance_chance: int = Field(default=100_000, ge=0, le=1_000_000)
    actor_time_limit_ms: int = Field(default=60_000, gt=0)
    sweeper_interval_seconds: int = Field(default=10, gt=0)
    sweeper_stuck_after_seconds: int = Field(default=60, gt=0)

    # SAPS File Storage (ADR-0006)
    s3_endpoint_url: str = "http://localhost:8333"
    s3_bucket: str = "invoices"
    s3_access_key: str = "local-test-access"
    s3_secret_key: SecretStr = SecretStr("local-test-secret")

    # Ports (ADR-0001)
    extraction_adapter: str = "dummy"
    erp_adapter: str = "dummy"
    fixtures_dir: Path = Path("fixtures")

    # Sessions and CSRF (ADR-0008)
    web_app_origin: str = "http://localhost:5173"
    session_idle_timeout_minutes: int = Field(default=30, gt=0)
    session_absolute_timeout_hours: int = Field(default=8, gt=0)
    session_cookie_secure: bool = True

    # Upload (SAPS-17)
    max_upload_size_mb: int = Field(default=10, gt=0)

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Settings are read once per process."""
    return Settings()
