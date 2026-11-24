"""Ports of the Single Sign-On: the Identity Provider and the cipher of stored tokens (SAPS-44, ADR-0011).

Only standard OpenID Connect is assumed, so Keycloak can be replaced or can broker another provider without
a change here (NFR-MAINT-001).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from saps.domain.identity import IdentityClaims


@dataclass(frozen=True)
class Tokens:
    """The validated result of a code exchange or a refresh; never logged or sent to the browser."""

    claims: IdentityClaims
    refresh_token: str
    id_token: str
    access_token_expires_at: datetime


class IdentityProviderUnavailableError(Exception):
    """The Identity Provider cannot be reached or answered with a server error (EC-07, EC-08)."""


class IdentityRejectedError(Exception):
    """The Identity Provider refused the code or refresh token, or a token is invalid (EC-02, EC-09)."""


class InvalidLogoutTokenError(Exception):
    """A back-channel logout token failed validation (EC-11)."""


class IdentityProvider(Protocol):
    async def authorization_url(self, *, state: str, nonce: str, code_challenge: str) -> str:
        """Where the browser signs in (authorization code flow with PKCE S256)."""
        ...

    async def exchange_code(self, *, code: str, code_verifier: str, nonce: str) -> Tokens: ...

    async def refresh(self, refresh_token: str) -> Tokens: ...

    async def logout_session_id(self, logout_token: str) -> str:
        """The Identity Provider session (`sid`) of a valid back-channel logout token."""
        ...

    async def end_session_url(self, *, id_token: str) -> str:
        """Where the browser ends the Identity Provider session and comes back to the SAPS Web App."""
        ...


class TokenCipher(Protocol):
    """Authenticated encryption of the stored tokens and of the short-lived sign-in cookie."""

    def encrypt(self, value: str) -> str: ...

    def decrypt(self, value: str, *, max_age_seconds: int | None = None) -> str | None:
        """The plain value, or None when it was tampered with, encrypted with another key, or is too old."""
        ...
