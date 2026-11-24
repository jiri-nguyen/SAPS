"""SAPS-42: the demo companies file (`fixtures/companies.json`)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from saps.adapters.demo.companies import DemoCompanies, load_demo_companies

FIXTURES = Path(__file__).parents[2] / "fixtures"


def test_the_demo_companies_are_valid() -> None:  # BR-01, BR-02, MTG-20270301-5
    companies = load_demo_companies(FIXTURES).companies
    assert [(c.code, c.name, c.email_domain, c.time_zone) for c in companies] == [
        ("vn", "Demo Vietnam", "vn.example.com", "Asia/Ho_Chi_Minh"),
        ("sg", "Demo Singapore", "sg.example.com", "Asia/Singapore"),
        ("my", "Demo Malaysia", "my.example.com", "Asia/Kuala_Lumpur"),
    ]
    for company in companies:
        assert company.mailbox_address == f"ap@{company.email_domain}"
        assert company.keycloak_group == f"/companies/{company.code}"
        assert sorted(u.role.value for u in company.users) == [
            "ACCOUNTING_MANAGER",
            "ACCOUNTING_MEMBER",
            "ACCOUNTING_MEMBER",
        ]
        assert all(u.username.endswith("@" + company.email_domain) for u in company.users)


def _company(code: str = "aa", **changes: object) -> dict[str, object]:
    domain = f"{code}.example.com"
    base: dict[str, object] = {
        "code": code,
        "name": f"Company {code}",
        "email_domain": domain,
        "keycloak_group": f"/companies/{code}",
        "mailbox_address": f"ap@{domain}",
        "time_zone": "UTC",
        "users": [{"username": f"m@{domain}", "display_name": "M", "role": "ACCOUNTING_MEMBER"}],
        "erp": ["*/erp/*.json"],
    }
    return {**base, **changes}


@pytest.mark.parametrize(
    ("companies", "error"),
    [
        ([_company(time_zone="Mars/Olympus")], "unknown time zone"),
        ([_company(code="AA")], "String should match pattern"),
        (
            [
                _company(
                    users=[
                        {"username": "m@other.example.com", "display_name": "M", "role": "ACCOUNTING_MEMBER"}
                    ]
                )
            ],
            "not in the domain",
        ),
        (
            [
                _company(),
                _company(
                    "bb",
                    email_domain="aa.example.com",
                    users=[
                        {"username": "x@aa.example.com", "display_name": "X", "role": "ACCOUNTING_MEMBER"}
                    ],
                ),
            ],
            "same email_domain",
        ),
        ([_company(), _company("bb", keycloak_group="/companies/aa")], "same keycloak_group"),
        ([_company(), _company("aa")], "same code"),
        ([], "at least 1 item"),
    ],
)
def test_inconsistent_companies_are_refused(companies: list[dict[str, object]], error: str) -> None:  # EC-05
    with pytest.raises(ValidationError, match=error):
        DemoCompanies.model_validate_json(json.dumps({"companies": companies}))


def test_two_companies_cannot_share_a_username(tmp_path: Path) -> None:
    shared = [{"username": "m@aa.example.com", "display_name": "M", "role": "ACCOUNTING_MEMBER"}]
    data = {"companies": [_company(), _company("bb", email_domain="aa.example.com", users=shared)]}
    (tmp_path / "companies.json").write_text(json.dumps(data))
    with pytest.raises(ValidationError):
        load_demo_companies(tmp_path)
