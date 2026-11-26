"""Settings read from environment variables (Developer Guide §6)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration of the SAPS API and SAPS Worker."""

    # `.env` is read from the repository root (when run from backend/) and from the working directory.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    # SAPS Database (ADR-0003, ADR-0005). `database_url` is the table owner (migrations, seed); the running
    # SAPS API and worker jobs use `app_database_url` (row-level security applies), the sweeper
    # `system_database_url` (SAPS-41).
    database_url: str = "postgresql+psycopg://saps:saps@localhost:5432/saps"
    app_database_url: str = "postgresql+psycopg://saps_app:saps-app-local@localhost:5432/saps"
    system_database_url: str = "postgresql+psycopg://saps_system:saps-system-local@localhost:5432/saps"
    app_db_password: SecretStr = SecretStr("saps-app-local")
    system_db_password: SecretStr = SecretStr("saps-system-local")

    # SAPS Message Broker and SAPS Worker (ADR-0004)
    redis_url: str = "redis://localhost:6379/0"
    dramatiq_heartbeat_timeout_ms: int = Field(default=30_000, gt=0)
    dramatiq_maintenance_chance: int = Field(default=100_000, ge=0, le=1_000_000)
    actor_time_limit_ms: int = Field(default=60_000, gt=0)
    process_invoice_max_retries: int = Field(default=5, gt=0)
    process_invoice_min_backoff_ms: int = Field(default=15_000, gt=0)
    process_invoice_max_backoff_ms: int = Field(default=300_000, gt=0)
    sweeper_interval_seconds: int = Field(default=10, gt=0)
    sweeper_stuck_after_seconds: int = Field(default=60, gt=0)
    sweeper_max_resends: int = Field(default=3, gt=0)

    # Invoice intake from company mailboxes (SAPS-45, ADR-0012): `none` or `imap` (`graph` later, SAPS-53).
    mail_adapter: str = "none"
    mail_poll_seconds: int = Field(default=60, gt=0)
    mail_batch_size: int = Field(default=50, gt=0)
    imap_host: str = "localhost"
    imap_port: int = Field(default=3143, gt=0)
    imap_ssl: bool = False
    imap_password: SecretStr = SecretStr("")

    # Processing calendar (SAPS-52): held invoices are released on open days, oldest first.
    hold_release_seconds: int = Field(default=60, gt=0)
    hold_release_batch: int = Field(default=200, gt=0)

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

    # Single Sign-On (SAPS-44, ADR-0011): the SAPS API is the OpenID Connect client of the Identity Provider.
    # The discovery document is read at the internal URL; tokens carry the public issuer.
    oidc_discovery_url: str = "http://localhost:8080/realms/saps/.well-known/openid-configuration"
    oidc_issuer: str = "http://localhost:8080/realms/saps"
    oidc_client_id: str = "saps-web"
    oidc_client_secret: SecretStr = SecretStr("")
    oidc_groups_claim: str = "groups"
    oidc_roles_claim: str = "roles"
    # Fernet key for the stored tokens and the sign-in cookie; required by the SAPS API
    # (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
    session_encryption_key: SecretStr | None = None

    # Password of the demo users in Keycloak (SAPS-43); empty → the demo seed is skipped
    seed_user_password: SecretStr | None = None

    # Upload (SAPS-17)
    max_upload_size_mb: int = Field(default=10, gt=0)

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Settings are read once per process."""
    return Settings()
