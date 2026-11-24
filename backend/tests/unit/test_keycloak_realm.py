"""SAPS-43: the Keycloak realm generated from the demo companies."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from saps.adapters.demo.companies import load_demo_companies
from saps.adapters.demo.keycloak_realm import build_realm, render_realm

BACKEND = Path(__file__).parents[2]
COMPANIES = load_demo_companies(BACKEND / "fixtures")
COMMITTED = BACKEND.parent / "deploy" / "keycloak" / "realm-saps.json"


@pytest.fixture(scope="module")
def realm() -> dict[str, Any]:
    return build_realm(COMPANIES)


def test_the_committed_realm_file_is_up_to_date() -> None:
    assert COMMITTED.read_text() == render_realm(COMPANIES), "run `make keycloak-realm` in backend/"


def test_the_realm_signs_in_with_brute_force_protection_and_no_registration(realm: dict[str, Any]) -> None:
    assert realm["realm"] == "saps" and realm["enabled"] is True
    assert realm["sslRequired"] == "external" and realm["registrationAllowed"] is False
    assert (realm["bruteForceProtected"], realm["permanentLockout"], realm["failureFactor"]) == (
        True,
        False,
        5,
    )
    assert (realm["accessTokenLifespan"], realm["ssoSessionIdleTimeout"], realm["ssoSessionMaxLifespan"]) == (
        300,
        1800,
        28800,
    )  # like the SAPS session of ADR-0011


def test_there_is_a_group_per_company_and_two_realm_roles(realm: dict[str, Any]) -> None:  # ADR-0010
    [companies] = realm["groups"]
    assert companies["path"] == "/companies"
    assert [(g["path"], g["attributes"]["company_code"]) for g in companies["subGroups"]] == [
        (c.keycloak_group, [c.code]) for c in COMPANIES.companies
    ]
    assert [r["name"] for r in realm["roles"]["realm"]] == ["ACCOUNTING_MEMBER", "ACCOUNTING_MANAGER"]


def test_the_client_is_confidential_with_the_authorization_code_flow_only(realm: dict[str, Any]) -> None:
    [client] = realm["clients"]
    assert client["clientId"] == "saps-web" and client["publicClient"] is False
    assert client["standardFlowEnabled"] is True
    assert not any(
        client[flag]
        for flag in ("implicitFlowEnabled", "directAccessGrantsEnabled", "serviceAccountsEnabled")
    )
    assert client["redirectUris"] == ["${WEB_APP_ORIGIN}/v1/session/callback"]
    assert client["attributes"]["pkce.code.challenge.method"] == "S256"
    assert client["attributes"]["backchannel.logout.url"] == "http://api:8000/v1/session/backchannel-logout"
    claims = {m["config"]["claim.name"]: m for m in client["protocolMappers"]}
    assert claims["groups"]["protocolMapper"] == "oidc-group-membership-mapper"
    assert claims["groups"]["config"]["full.path"] == "true"
    assert claims["roles"]["config"]["multivalued"] == "true"
    for mapper in claims.values():
        assert {
            mapper["config"][t] for t in ("id.token.claim", "access.token.claim", "userinfo.token.claim")
        } == {"true"}


def test_every_demo_user_has_its_company_group_and_role(realm: dict[str, Any]) -> None:
    expected = {u.username: (c.keycloak_group, u.role.value) for c in COMPANIES.companies for u in c.users}
    users = {u["username"]: u for u in realm["users"]}
    assert users.keys() == expected.keys() and len(users) == 9
    for username, (group, role) in expected.items():
        user = users[username]
        assert (user["groups"], user["realmRoles"]) == ([group], [role])
        assert user["email"] == username and user["emailVerified"] is True and user["enabled"] is True
        assert f"{user['firstName']} {user['lastName']}" in {
            u.display_name for c in COMPANIES.companies for u in c.users
        }


def test_no_secret_is_written_to_the_file(realm: dict[str, Any]) -> None:
    text = render_realm(COMPANIES)
    secrets = re.findall(r'"(?:secret|value)": "([^"]*)"', text)
    assert secrets and all(re.fullmatch(r"\$\{[A-Z_]+\}", s) for s in secrets), secrets  # placeholders only
    assert json.loads(text) == realm
