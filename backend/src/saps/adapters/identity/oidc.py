"""OpenID Connect client of the SAPS API (SAPS-44, ADR-0011).

Standard OpenID Connect only (discovery, authorization code with PKCE, refresh, RP-initiated logout,
back-channel logout), so any compliant provider works; Keycloak is configured, not coded against
(NFR-MAINT-001).

Server-to-server calls use the discovery document at `discovery_url` (inside Docker Compose:
`http://keycloak:8080/...`); the browser is sent to the authorization and end-session endpoints that
document names.
Tokens must carry the configured public `issuer`.
"""

import asyncio
import logging
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from joserfc import jwt
from joserfc.errors import InvalidKeyIdError, JoseError
from joserfc.jwk import KeySet

from saps.domain.identity import IdentityClaims
from saps.ports.identity import (
    IdentityProviderUnavailableError,
    IdentityRejectedError,
    InvalidLogoutTokenError,
    Tokens,
)

BACKCHANNEL_LOGOUT_EVENT = "http://schemas.openid.net/event/backchannel-logout"
SIGNING_ALGORITHMS = ("RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512")
LEEWAY_SECONDS = 30
LOGOUT_TOKEN_MAX_AGE_SECONDS = 300
JWKS_MIN_REFRESH_SECONDS = 60
TIMEOUT = httpx.Timeout(5.0)

log = logging.getLogger("saps.oidc")


class OidcIdentityProvider:
    def __init__(
        self,
        *,
        discovery_url: str,
        issuer: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        post_logout_redirect_uri: str,
        groups_claim: str = "groups",
        roles_claim: str = "roles",
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._discovery_url = discovery_url
        self._issuer = issuer
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._post_logout_redirect_uri = post_logout_redirect_uri
        self._groups_claim = groups_claim
        self._roles_claim = roles_claim
        self._transport = transport
        self._clock = clock
        self._metadata: dict[str, Any] | None = None
        self._keys: KeySet | None = None
        self._keys_fetched_at = 0.0
        self._lock = asyncio.Lock()

    # --- IdentityProvider port ------------------------------------------------------------------------------

    async def authorization_url(self, *, state: str, nonce: str, code_challenge: str) -> str:
        metadata = await self._discovery()
        query = urlencode(
            {
                "response_type": "code",
                "client_id": self._client_id,
                "redirect_uri": self._redirect_uri,
                "scope": "openid profile email",
                "state": state,
                "nonce": nonce,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )
        return f"{metadata['authorization_endpoint']}?{query}"

    async def exchange_code(self, *, code: str, code_verifier: str, nonce: str) -> Tokens:
        response = await self._token_request(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._redirect_uri,
                "code_verifier": code_verifier,
            }
        )
        return await self._tokens(response, nonce=nonce)

    async def refresh(self, refresh_token: str) -> Tokens:
        response = await self._token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})
        tokens = await self._tokens(response, nonce=None)
        if not tokens.refresh_token:  # a provider that does not rotate keeps the old one valid
            tokens = Tokens(tokens.claims, refresh_token, tokens.id_token, tokens.access_token_expires_at)
        return tokens

    async def logout_session_id(self, logout_token: str) -> str:
        try:
            claims = await self._verified_claims(logout_token)
            self._check_issuer_and_audience(claims)
            iat = claims.get("iat")
            if not isinstance(iat, int | float) or abs(self._clock() - iat) > LOGOUT_TOKEN_MAX_AGE_SECONDS:
                raise IdentityRejectedError("logout token too old")
            events = claims.get("events")
            if not isinstance(events, Mapping) or BACKCHANNEL_LOGOUT_EVENT not in events:
                raise IdentityRejectedError("not a back-channel logout token")
            if "nonce" in claims:
                raise IdentityRejectedError("a logout token has no nonce")
            sid = claims.get("sid")
            if not isinstance(sid, str) or not sid:
                raise IdentityRejectedError("no session id")
        except IdentityRejectedError as exc:
            raise InvalidLogoutTokenError(str(exc)) from exc
        return sid

    async def end_session_url(self, *, id_token: str) -> str:
        metadata = await self._discovery()
        params = {"client_id": self._client_id, "post_logout_redirect_uri": self._post_logout_redirect_uri}
        if id_token:
            params["id_token_hint"] = id_token
        endpoint = metadata.get("end_session_endpoint")
        if not endpoint:
            return self._post_logout_redirect_uri
        return f"{endpoint}?{urlencode(params)}"

    # --- HTTP -----------------------------------------------------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=TIMEOUT, transport=self._transport)

    async def _get_json(self, url: str) -> dict[str, Any]:
        try:
            async with self._client() as client:
                response = await client.get(url)
        except httpx.HTTPError as exc:
            raise IdentityProviderUnavailableError(f"{type(exc).__name__} for {url}") from exc
        if response.status_code != httpx.codes.OK:
            raise IdentityProviderUnavailableError(f"HTTP {response.status_code} for {url}")
        try:
            body = response.json()
        except ValueError as exc:
            raise IdentityProviderUnavailableError(f"no JSON from {url}") from exc
        if not isinstance(body, dict):
            raise IdentityProviderUnavailableError(f"unexpected JSON from {url}")
        return body

    async def _discovery(self) -> dict[str, Any]:
        if self._metadata is None:
            metadata = await self._get_json(self._discovery_url)
            missing = [
                k for k in ("authorization_endpoint", "token_endpoint", "jwks_uri") if k not in metadata
            ]
            if missing:
                raise IdentityProviderUnavailableError(f"discovery document without {', '.join(missing)}")
            self._metadata = metadata
        return self._metadata

    async def _key_set(self, *, refresh: bool = False) -> KeySet:
        async with self._lock:
            stale = self._clock() - self._keys_fetched_at >= JWKS_MIN_REFRESH_SECONDS
            if self._keys is None or (refresh and stale):
                metadata = await self._discovery()
                body = await self._get_json(metadata["jwks_uri"])
                try:
                    keys = [k for k in body.get("keys", []) if k.get("use", "sig") == "sig"]
                    self._keys = KeySet.import_key_set({"keys": keys})
                except (JoseError, ValueError, TypeError, AttributeError) as exc:
                    raise IdentityProviderUnavailableError("unreadable key set") from exc
                self._keys_fetched_at = self._clock()
            return self._keys

    async def _token_request(self, form: dict[str, str]) -> dict[str, Any]:
        metadata = await self._discovery()
        try:
            async with self._client() as client:
                response = await client.post(
                    metadata["token_endpoint"], data=form, auth=(self._client_id, self._client_secret)
                )
        except httpx.HTTPError as exc:
            raise IdentityProviderUnavailableError(type(exc).__name__) from exc
        if response.status_code == httpx.codes.BAD_REQUEST:
            error = _error_code(response)
            log.info("token_request_refused", extra={"error": error})
            raise IdentityRejectedError(error)
        if response.status_code != httpx.codes.OK:
            log.warning("token_request_failed", extra={"status": response.status_code})
            raise IdentityProviderUnavailableError(f"HTTP {response.status_code} from the token endpoint")
        try:
            body = response.json()
        except ValueError as exc:
            raise IdentityProviderUnavailableError("no JSON from the token endpoint") from exc
        if not isinstance(body, dict):
            raise IdentityProviderUnavailableError("unexpected JSON from the token endpoint")
        return body

    # --- Tokens ---------------------------------------------------------------------------------------------

    async def _tokens(self, response: dict[str, Any], *, nonce: str | None) -> Tokens:
        id_token = response.get("id_token")
        if not isinstance(id_token, str):
            raise IdentityRejectedError("no ID token")
        claims = await self._verified_claims(id_token)
        self._check_issuer_and_audience(claims)
        exp = claims.get("exp")
        if not isinstance(exp, int | float) or exp + LEEWAY_SECONDS < self._clock():
            raise IdentityRejectedError("ID token expired")
        if not isinstance(claims.get("sub"), str) or not claims["sub"]:
            raise IdentityRejectedError("no subject")
        if nonce is not None and claims.get("nonce") != nonce:
            raise IdentityRejectedError("nonce mismatch")
        expires_in = response.get("expires_in")
        lifetime = expires_in if isinstance(expires_in, int) and expires_in > 0 else 60
        now = datetime.fromtimestamp(self._clock(), UTC)
        return Tokens(
            claims=self._identity(claims),
            refresh_token=str(response.get("refresh_token") or ""),
            id_token=id_token,
            access_token_expires_at=now + timedelta(seconds=lifetime),
        )

    async def _verified_claims(self, token: str) -> dict[str, Any]:
        """Signature checked with the provider's keys; the key set is fetched again once for a new key id."""
        try:
            try:
                decoded = jwt.decode(token, await self._key_set(), algorithms=SIGNING_ALGORITHMS)
            except InvalidKeyIdError:
                decoded = jwt.decode(token, await self._key_set(refresh=True), algorithms=SIGNING_ALGORITHMS)
        except JoseError as exc:
            raise IdentityRejectedError(f"invalid token: {type(exc).__name__}") from exc
        return dict(decoded.claims)

    def _check_issuer_and_audience(self, claims: Mapping[str, Any]) -> None:
        if claims.get("iss") != self._issuer:
            raise IdentityRejectedError("issuer mismatch")
        audience = claims.get("aud")
        audiences = audience if isinstance(audience, list) else [audience]
        if self._client_id not in audiences:
            raise IdentityRejectedError("audience mismatch")
        if len(audiences) > 1 and claims.get("azp") not in (None, self._client_id):
            raise IdentityRejectedError("authorized party mismatch")

    def _identity(self, claims: Mapping[str, Any]) -> IdentityClaims:
        email = claims.get("email")
        if not isinstance(email, str) or claims.get("email_verified") is False:
            email = ""  # an unverified address never matches a company domain (BR-02)
        name = claims.get("name") or claims.get("preferred_username") or email
        return IdentityClaims(
            issuer=str(claims["iss"]),
            subject=str(claims["sub"]),
            email=email,
            display_name=str(name),
            groups=_strings(claims.get(self._groups_claim)),
            roles=_strings(claims.get(self._roles_claim)),
            session_id=claims.get("sid") if isinstance(claims.get("sid"), str) else None,
        )


def _strings(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(v for v in value if isinstance(v, str))
    return ()


def _error_code(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return "invalid_request"
    error = body.get("error") if isinstance(body, dict) else None
    return error if isinstance(error, str) else "invalid_request"
