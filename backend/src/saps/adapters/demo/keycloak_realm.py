"""The Keycloak realm `saps` for the demo companies (SAPS-43, ADR-0010, ADR-0011).

Generated from `companies.json`, so companies, groups and users cannot drift. Passwords and the client
secret are placeholders (`${SEED_USER_PASSWORD}`, `${KEYCLOAK_CLIENT_SECRET}`) that Keycloak replaces from
environment variables at import; nothing secret is written to the repository.
"""

import json
from typing import Any

from saps.adapters.demo.companies import DemoCompanies
from saps.domain.users import Role

REALM = "saps"
CLIENT_ID = "saps-web"
COMPANIES_GROUP = "companies"
GROUPS_CLAIM = "groups"
ROLES_CLAIM = "roles"
USER_PASSWORD = "${SEED_USER_PASSWORD}"  # noqa: S105  (placeholder, replaced by Keycloak at import)
CLIENT_SECRET = "${KEYCLOAK_CLIENT_SECRET}"  # noqa: S105  (placeholder, replaced by Keycloak at import)
WEB_APP_ORIGIN = "${WEB_APP_ORIGIN}"
BACKCHANNEL_LOGOUT_URL = "http://api:8000/v1/session/backchannel-logout"  # specified in SAPS-44

_ROLE_DESCRIPTION = {
    Role.ACCOUNTING_MEMBER: "Handles exceptions and gives the final review of invoices",
    Role.ACCOUNTING_MANAGER: "Approves invoices above the threshold and changes the matching settings",
}


def _claim_mapper(name: str, mapper: str, claim: str, **config: str) -> dict[str, Any]:
    return {
        "name": name,
        "protocol": "openid-connect",
        "protocolMapper": mapper,
        "consentRequired": False,
        "config": {
            "claim.name": claim,
            "jsonType.label": "String",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "userinfo.token.claim": "true",
            **config,
        },
    }


def _client() -> dict[str, Any]:
    return {
        "clientId": CLIENT_ID,
        "name": "SAPS Web App and SAPS API",
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,  # confidential: the SAPS API is the client (ADR-0011)
        "secret": CLIENT_SECRET,
        "standardFlowEnabled": True,
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False,
        "redirectUris": [f"{WEB_APP_ORIGIN}/v1/session/callback"],
        "webOrigins": [],
        "attributes": {
            "pkce.code.challenge.method": "S256",
            "post.logout.redirect.uris": f"{WEB_APP_ORIGIN}/*",
            "backchannel.logout.url": BACKCHANNEL_LOGOUT_URL,
            "backchannel.logout.session.required": "true",
        },
        "defaultClientScopes": ["web-origins", "acr", "profile", "roles", "email"],
        "protocolMappers": [
            _claim_mapper("groups", "oidc-group-membership-mapper", GROUPS_CLAIM, **{"full.path": "true"}),
            _claim_mapper("realm roles", "oidc-usermodel-realm-role-mapper", ROLES_CLAIM, multivalued="true"),
        ],
    }


def build_realm(companies: DemoCompanies) -> dict[str, Any]:
    """The realm import file: a group per company, realm roles, the client of the SAPS API, the demo users."""
    users: list[dict[str, Any]] = []
    for company in companies.companies:
        for user in company.users:
            first_name, _, last_name = user.display_name.partition(" ")
            users.append(
                {
                    "username": user.username,
                    "email": user.username,
                    "emailVerified": True,
                    "enabled": True,
                    "firstName": first_name,
                    "lastName": last_name,
                    "credentials": [{"type": "password", "value": USER_PASSWORD, "temporary": False}],
                    "groups": [company.keycloak_group],
                    "realmRoles": [user.role.value],
                }
            )
    return {
        "realm": REALM,
        "displayName": "Smart-AP-Suite",
        "enabled": True,
        "sslRequired": "external",
        "registrationAllowed": False,
        "loginWithEmailAllowed": True,
        "duplicateEmailsAllowed": False,
        "resetPasswordAllowed": False,
        # Brute-force protection of the sign-in (resolves TD-03): temporary lockout after repeated failures.
        "bruteForceProtected": True,
        "permanentLockout": False,
        "failureFactor": 5,
        "waitIncrementSeconds": 60,
        "maxFailureWaitSeconds": 900,
        "minimumQuickLoginWaitSeconds": 60,
        # Like the SAPS session (ADR-0011): 30 minutes idle, 8 hours at most; access token 5 minutes.
        "accessTokenLifespan": 300,
        "ssoSessionIdleTimeout": 1800,
        "ssoSessionMaxLifespan": 28800,
        "roles": {
            "realm": [
                {"name": role.value, "description": _ROLE_DESCRIPTION[role]}
                for role in (Role.ACCOUNTING_MEMBER, Role.ACCOUNTING_MANAGER)
            ]
        },
        "groups": [
            {
                "name": COMPANIES_GROUP,
                "path": f"/{COMPANIES_GROUP}",
                "subGroups": [
                    {
                        "name": company.keycloak_group.rsplit("/", 1)[-1],
                        "path": company.keycloak_group,
                        "attributes": {"company_code": [company.code]},
                    }
                    for company in companies.companies
                ],
            }
        ],
        "clients": [_client()],
        "users": users,
    }


def render_realm(companies: DemoCompanies) -> str:
    """The realm file as committed: stable key order, two-space indent, final newline."""
    return json.dumps(build_realm(companies), indent=2, ensure_ascii=False) + "\n"
