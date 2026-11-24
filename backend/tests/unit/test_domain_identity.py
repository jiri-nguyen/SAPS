"""Who may sign in (SAPS-44 BR-02, TS-01) and the return path guard (EC-10)."""

from dataclasses import replace
from uuid import uuid4

import pytest

from saps.domain.identity import (
    CompanyRef,
    IdentityClaims,
    SignInRefusal,
    SignInRefusedError,
    accept,
    company_group,
    safe_return_to,
)
from saps.domain.users import Role

VN = CompanyRef(uuid4(), "Demo Vietnam", "/companies/vn", "vn.example.com", True)
CLAIMS = IdentityClaims(
    issuer="http://idp.test/realms/saps",
    subject="s",
    email="Member1@VN.example.com",
    display_name="M1",
    groups=("/companies/vn", "/other/group"),
    roles=("ACCOUNTING_MEMBER", "default-roles-saps"),
)


def test_one_company_group_matching_domain_and_one_role_are_accepted() -> None:
    acceptance = accept(CLAIMS, VN)
    assert acceptance.company == VN and acceptance.role is Role.ACCOUNTING_MEMBER


@pytest.mark.parametrize(
    ("claims", "company", "reason"),
    [
        (replace(CLAIMS, groups=()), VN, SignInRefusal.NO_COMPANY),
        (replace(CLAIMS, groups=("/companies/vn", "/companies/sg")), VN, SignInRefusal.NO_COMPANY),
        (CLAIMS, None, SignInRefusal.NO_COMPANY),  # unknown company
        (CLAIMS, replace(VN, is_active=False), SignInRefusal.NO_COMPANY),
        (CLAIMS, replace(VN, keycloak_group="/companies/sg"), SignInRefusal.NO_COMPANY),
        (replace(CLAIMS, email="member1@sg.example.com"), VN, SignInRefusal.WRONG_DOMAIN),
        (replace(CLAIMS, email="member1@evil.vn.example.com"), VN, SignInRefusal.WRONG_DOMAIN),
        (replace(CLAIMS, email=""), VN, SignInRefusal.WRONG_DOMAIN),
        (replace(CLAIMS, roles=("offline_access",)), VN, SignInRefusal.NO_ROLE),
        (replace(CLAIMS, roles=("ACCOUNTING_MEMBER", "ACCOUNTING_MANAGER")), VN, SignInRefusal.NO_ROLE),
    ],
)
def test_broken_rules_are_refused_with_their_reason(
    claims: IdentityClaims, company: CompanyRef | None, reason: SignInRefusal
) -> None:
    with pytest.raises(SignInRefusedError) as caught:
        accept(claims, company)
    assert caught.value.reason is reason


def test_company_group_only_when_there_is_exactly_one() -> None:
    assert company_group(CLAIMS) == "/companies/vn"
    assert company_group(replace(CLAIMS, groups=("/companies/vn", "/companies/sg"))) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "/"),
        ("", "/"),
        ("/invoices/1?x=2", "/invoices/1?x=2"),
        ("//evil.example", "/"),
        ("https://evil.example", "/"),
        ("/\\evil.example", "/"),
        ("/a\r\nSet-Cookie: x", "/"),
    ],
)
def test_return_path_is_a_path_of_the_web_app(value: str | None, expected: str) -> None:
    assert safe_return_to(value) == expected
