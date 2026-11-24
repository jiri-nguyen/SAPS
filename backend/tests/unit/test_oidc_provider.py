"""OpenID Connect adapter against a test OpenID provider (SAPS-44 TS-02, TS-03, TS-05).

The provider is an httpx MockTransport with its own RSA keys: discovery, key set and token endpoint.
"""

from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from joserfc import jwt
from joserfc.jwk import RSAKey

from saps.adapters.identity.oidc import BACKCHANNEL_LOGOUT_EVENT, OidcIdentityProvider
from saps.ports.identity import (
    IdentityProviderUnavailableError,
    IdentityRejectedError,
    InvalidLogoutTokenError,
)

NOW = 1_800_000_000.0
PUBLIC = "http://localhost:8080/realms/saps"
INTERNAL = "http://keycloak:8080/realms/saps"
CLIENT = "saps-web"
KEY = RSAKey.generate_key(2048, parameters={"kid": "k1", "alg": "RS256", "use": "sig"})


class FakeIdp:
    def __init__(self) -> None:
        self.keys = [KEY]
        self.token_response: tuple[int, Any] = (200, {})
        self.requests: list[httpx.Request] = []
        self.jwks_calls = 0
        self.down = False
        self.discovery: dict[str, Any] = {
            "issuer": PUBLIC,
            "authorization_endpoint": f"{PUBLIC}/protocol/openid-connect/auth",
            "end_session_endpoint": f"{PUBLIC}/protocol/openid-connect/logout",
            "token_endpoint": f"{INTERNAL}/protocol/openid-connect/token",
            "jwks_uri": f"{INTERNAL}/protocol/openid-connect/certs",
        }

    def token_requests(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.path.endswith("/token")]

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.down:
            raise httpx.ConnectError("refused", request=request)
        path = request.url.path
        if path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(200, json=self.discovery)
        if path.endswith("/certs"):
            self.jwks_calls += 1
            return httpx.Response(200, json={"keys": [k.as_dict(private=False) for k in self.keys]})
        if path.endswith("/token"):
            code, body = self.token_response
            return (
                httpx.Response(code, json=body)
                if not isinstance(body, str)
                else httpx.Response(code, text=body)
            )
        return httpx.Response(404)


def _claims(**overrides: Any) -> dict[str, Any]:
    claims = {
        "iss": PUBLIC,
        "aud": CLIENT,
        "sub": "sub-1",
        "exp": int(NOW) + 300,
        "iat": int(NOW),
        "nonce": "n-1",
        "sid": "sid-1",
        "email": "member1@vn.example.com",
        "email_verified": True,
        "name": "Accounting Member 1",
        "groups": ["/companies/vn"],
        "roles": ["ACCOUNTING_MEMBER", "offline_access"],
    }
    claims.update(overrides)
    return {k: v for k, v in claims.items() if v is not None}


def _sign(claims: dict[str, Any], key: RSAKey = KEY, kid: str = "k1") -> str:
    return jwt.encode({"alg": "RS256", "kid": kid}, claims, key)


def _token_body(**overrides: Any) -> dict[str, Any]:
    return {
        "id_token": _sign(_claims()),
        "refresh_token": "rt-1",
        "access_token": "at",
        "expires_in": 300,
        **overrides,
    }


@pytest.fixture
def idp() -> FakeIdp:
    return FakeIdp()


@pytest.fixture
def provider(idp: FakeIdp) -> OidcIdentityProvider:
    return OidcIdentityProvider(
        discovery_url=f"{INTERNAL}/.well-known/openid-configuration",
        issuer=PUBLIC,
        client_id=CLIENT,
        client_secret="client-secret",  # noqa: S106  (test value)
        redirect_uri="http://localhost:5173/v1/session/callback",
        post_logout_redirect_uri="http://localhost:5173/",
        transport=httpx.MockTransport(idp.handler),
        clock=lambda: NOW,
    )


async def test_authorization_url_uses_the_public_endpoint_with_pkce(provider: OidcIdentityProvider) -> None:
    url = urlsplit(await provider.authorization_url(state="s", nonce="n", code_challenge="c"))
    query = {k: v[0] for k, v in parse_qs(url.query).items()}
    assert f"{url.scheme}://{url.netloc}{url.path}" == f"{PUBLIC}/protocol/openid-connect/auth"
    assert query == {
        "response_type": "code",
        "client_id": CLIENT,
        "redirect_uri": "http://localhost:5173/v1/session/callback",
        "scope": "openid profile email",
        "state": "s",
        "nonce": "n",
        "code_challenge": "c",
        "code_challenge_method": "S256",
    }


async def test_code_exchange_validates_the_id_token(idp: FakeIdp, provider: OidcIdentityProvider) -> None:
    idp.token_response = (200, _token_body())
    tokens = await provider.exchange_code(code="code-1", code_verifier="v-1", nonce="n-1")
    claims = tokens.claims
    assert (claims.issuer, claims.subject, claims.email, claims.display_name) == (
        PUBLIC,
        "sub-1",
        "member1@vn.example.com",
        "Accounting Member 1",
    )
    assert claims.groups == ("/companies/vn",) and claims.roles == ("ACCOUNTING_MEMBER", "offline_access")
    assert claims.session_id == "sid-1" and tokens.refresh_token == "rt-1"  # noqa: S105  (test value)
    assert tokens.access_token_expires_at.timestamp() == NOW + 300
    request = idp.token_requests()[-1]
    assert request.url.host == "keycloak"  # server-to-server through the internal URL
    assert request.headers["authorization"].startswith("Basic ")
    form = parse_qs(request.content.decode())
    assert form["grant_type"] == ["authorization_code"] and form["code_verifier"] == ["v-1"]
    assert idp.jwks_calls == 1
    await provider.exchange_code(code="code-2", code_verifier="v", nonce="n-1")
    assert idp.jwks_calls == 1  # cached


@pytest.mark.parametrize(
    "id_token",
    [
        _sign(_claims(iss="http://evil.example/realms/saps")),
        _sign(_claims(aud="another-client")),
        _sign(_claims(aud=[CLIENT, "other"], azp="other")),
        _sign(_claims(nonce="replayed")),
        _sign(_claims(exp=int(NOW) - 120)),
        _sign(_claims(sub=None)),
        _sign(_claims(), key=RSAKey.generate_key(2048), kid="k1"),  # wrong signature
        "not-a-jwt",
    ],
)
async def test_invalid_id_tokens_are_rejected(
    idp: FakeIdp, provider: OidcIdentityProvider, id_token: str
) -> None:
    idp.token_response = (200, _token_body(id_token=id_token))
    with pytest.raises(IdentityRejectedError):
        await provider.exchange_code(code="c", code_verifier="v", nonce="n-1")


async def test_a_new_signing_key_is_fetched_once(idp: FakeIdp, provider: OidcIdentityProvider) -> None:
    idp.token_response = (200, _token_body())
    await provider.exchange_code(code="c", code_verifier="v", nonce="n-1")
    rotated = RSAKey.generate_key(2048, parameters={"kid": "k2", "alg": "RS256", "use": "sig"})
    idp.keys = [KEY, rotated]
    provider._keys_fetched_at = NOW - 120  # the last fetch is older than the minimum interval
    idp.token_response = (200, _token_body(id_token=_sign(_claims(), key=rotated, kid="k2")))
    tokens = await provider.exchange_code(code="c", code_verifier="v", nonce="n-1")
    assert tokens.claims.subject == "sub-1" and idp.jwks_calls == 2
    idp.token_response = (200, _token_body(id_token=_sign(_claims(), key=rotated, kid="k3")))
    with pytest.raises(IdentityRejectedError):  # unknown again, within the minimum interval: no new fetch
        await provider.exchange_code(code="c", code_verifier="v", nonce="n-1")
    assert idp.jwks_calls == 2


async def test_refresh_keeps_the_old_refresh_token_when_none_is_returned(
    idp: FakeIdp, provider: OidcIdentityProvider
) -> None:
    idp.token_response = (200, _token_body(id_token=_sign(_claims(nonce=None)), refresh_token=None))
    tokens = await provider.refresh("rt-old")
    assert tokens.refresh_token == "rt-old"  # noqa: S105  (test value)
    assert parse_qs(idp.token_requests()[-1].content.decode())["grant_type"] == ["refresh_token"]


async def test_unverified_email_never_matches_a_domain(idp: FakeIdp, provider: OidcIdentityProvider) -> None:
    idp.token_response = (200, _token_body(id_token=_sign(_claims(email_verified=False))))
    tokens = await provider.exchange_code(code="c", code_verifier="v", nonce="n-1")
    assert tokens.claims.email == ""


@pytest.mark.parametrize(
    ("response", "error"),
    [
        ((400, {"error": "invalid_grant"}), IdentityRejectedError),
        ((400, "not json"), IdentityRejectedError),
        ((200, {"access_token": "at"}), IdentityRejectedError),  # no ID token
        ((401, {"error": "unauthorized_client"}), IdentityProviderUnavailableError),
        ((503, "down"), IdentityProviderUnavailableError),
        ((200, "not json"), IdentityProviderUnavailableError),
        ((200, ["a list"]), IdentityProviderUnavailableError),
    ],
)
async def test_token_endpoint_errors(
    idp: FakeIdp, provider: OidcIdentityProvider, response: tuple[int, Any], error: type[Exception]
) -> None:
    idp.token_response = response
    with pytest.raises(error):
        await provider.refresh("rt")


async def test_an_unreachable_or_broken_provider_is_unavailable(
    idp: FakeIdp, provider: OidcIdentityProvider
) -> None:
    idp.down = True
    with pytest.raises(IdentityProviderUnavailableError):
        await provider.authorization_url(state="s", nonce="n", code_challenge="c")
    idp.down = False
    del idp.discovery["jwks_uri"]
    with pytest.raises(IdentityProviderUnavailableError):
        await provider.authorization_url(state="s", nonce="n", code_challenge="c")


async def test_discovery_and_key_set_must_be_json_objects(idp: FakeIdp) -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/certs"):
            return httpx.Response(200, json={"keys": [{"kty": "nope"}]})
        if "openid-configuration" in request.url.path:
            return idp.handler(request)
        return httpx.Response(200, text="[1]")

    provider = OidcIdentityProvider(
        discovery_url=f"{INTERNAL}/.well-known/openid-configuration",
        issuer=PUBLIC,
        client_id=CLIENT,
        client_secret="s",  # noqa: S106
        redirect_uri="r",
        post_logout_redirect_uri="p",
        transport=httpx.MockTransport(broken),
        clock=lambda: NOW,
    )
    with pytest.raises(IdentityProviderUnavailableError):
        await provider.logout_session_id(_sign(_claims()))  # unreadable key set
    for body, status in ((b"[1]", 200), (b"{", 200), (b"{}", 500)):

        def answer(request: httpx.Request, body: bytes = body, status: int = status) -> httpx.Response:
            return httpx.Response(status, content=body)

        bad = OidcIdentityProvider(
            discovery_url="http://x/.well-known/openid-configuration",
            issuer=PUBLIC,
            client_id=CLIENT,
            client_secret="s",  # noqa: S106
            redirect_uri="r",
            post_logout_redirect_uri="p",
            transport=httpx.MockTransport(answer),
        )
        with pytest.raises(IdentityProviderUnavailableError):
            await bad.authorization_url(state="s", nonce="n", code_challenge="c")


def _logout_claims(**overrides: Any) -> dict[str, Any]:
    claims = {
        "iss": PUBLIC,
        "aud": CLIENT,
        "iat": int(NOW),
        "jti": "j-1",
        "sid": "sid-1",
        "sub": "sub-1",
        "events": {BACKCHANNEL_LOGOUT_EVENT: {}},
    }
    claims.update(overrides)
    return {k: v for k, v in claims.items() if v is not None}


async def test_a_valid_logout_token_names_the_session(provider: OidcIdentityProvider) -> None:
    assert await provider.logout_session_id(_sign(_logout_claims())) == "sid-1"


@pytest.mark.parametrize(
    "claims",
    [
        _logout_claims(iss="http://evil.example"),
        _logout_claims(aud="other"),
        _logout_claims(iat=int(NOW) - 3600),
        _logout_claims(iat=None),
        _logout_claims(events=None),
        _logout_claims(events={"other": {}}),
        _logout_claims(nonce="n"),
        _logout_claims(sid=None),
    ],
)
async def test_invalid_logout_tokens_are_refused(
    provider: OidcIdentityProvider, claims: dict[str, Any]
) -> None:
    with pytest.raises(InvalidLogoutTokenError):
        await provider.logout_session_id(_sign(claims))


async def test_end_session_url(idp: FakeIdp, provider: OidcIdentityProvider) -> None:
    url = urlsplit(await provider.end_session_url(id_token="id-1"))  # noqa: S106  (test value)
    assert url.netloc == "localhost:8080"
    assert parse_qs(url.query) == {
        "client_id": [CLIENT],
        "post_logout_redirect_uri": ["http://localhost:5173/"],
        "id_token_hint": ["id-1"],
    }
    assert "id_token_hint" not in await provider.end_session_url(id_token="")


async def test_without_end_session_endpoint_the_browser_goes_back_to_the_web_app(
    idp: FakeIdp, provider: OidcIdentityProvider
) -> None:
    del idp.discovery["end_session_endpoint"]
    assert await provider.end_session_url(id_token="x") == "http://localhost:5173/"  # noqa: S106  (test value)
