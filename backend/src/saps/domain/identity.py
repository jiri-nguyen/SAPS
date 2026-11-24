"""Who may sign in through the Identity Provider (SAPS-44 BR-02, ADR-0010). Pure domain code (ADR-0001)."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from saps.domain.users import Role

COMPANIES_GROUP_PREFIX = "/companies/"


class SignInRefusal(StrEnum):
    """The reason code the Web App shows after a failed sign-in (SAPS-44 §3.3)."""

    CANCELLED = "cancelled"
    EXPIRED = "expired"
    NO_COMPANY = "no_company"
    WRONG_DOMAIN = "wrong_domain"
    NO_ROLE = "no_role"
    UNAVAILABLE = "unavailable"


class SignInRefusedError(Exception):
    def __init__(self, reason: SignInRefusal) -> None:
        super().__init__(reason.value)
        self.reason = reason


@dataclass(frozen=True)
class IdentityClaims:
    """Validated claims of an ID token (or of a refreshed one)."""

    issuer: str
    subject: str
    email: str
    display_name: str
    groups: tuple[str, ...]
    roles: tuple[str, ...]
    session_id: str | None = None


@dataclass(frozen=True)
class CompanyRef:
    """A company as the sign-in sees it: its group in the Identity Provider and its e-mail domain."""

    tenant_id: UUID
    name: str
    keycloak_group: str
    email_domain: str
    is_active: bool


@dataclass(frozen=True)
class Acceptance:
    company: CompanyRef
    role: Role


def accept(claims: IdentityClaims, company: CompanyRef | None) -> Acceptance:
    """Exactly one company group of an active company, an e-mail in its domain, exactly one role (BR-02).

    `company` is the company of `company_group(claims)`, looked up by the caller. Raises `SignInRefusedError`
    with the reason of the first rule that fails (EC-03 to EC-05).
    """
    group = company_group(claims)
    if group is None or company is None or company.keycloak_group != group or not company.is_active:
        raise SignInRefusedError(SignInRefusal.NO_COMPANY)
    _, at, domain = claims.email.rpartition("@")
    if not at or domain.lower() != company.email_domain.lower():
        raise SignInRefusedError(SignInRefusal.WRONG_DOMAIN)
    roles = _known_roles(claims.roles)
    if len(roles) != 1:
        raise SignInRefusedError(SignInRefusal.NO_ROLE)
    return Acceptance(company=company, role=roles.pop())


def _known_roles(values: Iterable[str]) -> set[Role]:
    known = {role.value: role for role in Role}
    return {known[value] for value in values if value in known}


def company_group(claims: IdentityClaims) -> str | None:
    """The single company group of the claims, if there is exactly one."""
    groups = {g for g in claims.groups if g.startswith(COMPANIES_GROUP_PREFIX)}
    return groups.pop() if len(groups) == 1 else None


def safe_return_to(value: str | None) -> str:
    """Only a path of the SAPS Web App; anything else (another site, a scheme) goes to `/` (EC-10)."""
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value:
        return "/"
    if any(ord(ch) < 0x20 for ch in value):
        return "/"
    return value
