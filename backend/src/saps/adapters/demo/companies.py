"""Demo companies of Phase 2 (SAPS-42).

`<FIXTURES_DIR>/companies.json` is read by the seed and the Dummy ERP Adapter.

Demo data only: domains under `example.com` (RFC 2606), no real companies (public repository).
"""

from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from saps.domain.users import Role

COMPANIES_FILE = "companies.json"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DemoUser(_Model):
    username: str = Field(min_length=3, max_length=100)
    display_name: str = Field(min_length=1, max_length=200)
    role: Role


class DemoCompany(_Model):
    code: str = Field(pattern=r"^[a-z][a-z0-9-]{1,19}$")
    name: str = Field(min_length=1, max_length=200)
    email_domain: str = Field(pattern=r"^[a-z0-9.-]+\.[a-z]{2,}$", max_length=255)
    keycloak_group: str = Field(pattern=r"^/[A-Za-z0-9/_-]+$", max_length=255)
    mailbox_address: str = Field(pattern=r"^[^@\s]+@[a-z0-9.-]+$", max_length=320)
    time_zone: str
    users: list[DemoUser] = Field(min_length=1)
    erp: list[str] = Field(min_length=1, description="Globs of ERP fixture files, relative to FIXTURES_DIR")

    @field_validator("time_zone")
    @classmethod
    def _known_time_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown time zone {value!r}") from exc
        return value

    @model_validator(mode="after")
    def _users_in_the_domain(self) -> DemoCompany:
        for user in self.users:
            if not user.username.endswith("@" + self.email_domain):
                raise ValueError(f"user {user.username} is not in the domain {self.email_domain}")
        return self


class DemoCompanies(_Model):
    companies: list[DemoCompany] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> DemoCompanies:
        for field in ("code", "email_domain", "keycloak_group", "mailbox_address"):
            values = [getattr(c, field) for c in self.companies]
            if len(values) != len(set(values)):
                raise ValueError(f"two companies share the same {field}")
        usernames = [u.username for c in self.companies for u in c.users]
        if len(usernames) != len(set(usernames)):
            raise ValueError("two demo users share the same username")
        return self


def load_demo_companies(fixtures_dir: Path) -> DemoCompanies:
    return DemoCompanies.model_validate_json((fixtures_dir / COMPANIES_FILE).read_bytes())
