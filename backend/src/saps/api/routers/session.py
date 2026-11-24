"""Session operations: Single Sign-On through the Identity Provider, getSession, deleteSession and
back-channel logout (SAPS-44, ADR-0011)."""

import logging
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Form, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from saps.api.deps import SESSION_COOKIE, Auth, User, session_policy
from saps.api.schemas import SignOut, UserAccount
from saps.application.auth import SIGN_IN_MAX_AGE_SECONDS
from saps.config import get_settings
from saps.domain.identity import SignInRefusal, SignInRefusedError
from saps.ports.identity import IdentityProviderUnavailableError, InvalidLogoutTokenError

router = APIRouter(prefix="/v1/session", tags=["Session"])
log = logging.getLogger("saps.api.session")

SIGN_IN_COOKIE = "saps_sign_in"
SIGN_IN_COOKIE_PATH = "/v1/session"
BACKCHANNEL_LOGOUT_PATH = "/v1/session/backchannel-logout"


def _secure() -> bool:
    return get_settings().session_cookie_secure


def _refused(reason: SignInRefusal) -> RedirectResponse:
    """Back to the sign-in page of the SAPS Web App with the reason code (SAPS-44 §3.3)."""
    response = RedirectResponse(f"/?signIn={quote(reason.value)}", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(
        SIGN_IN_COOKIE, path=SIGN_IN_COOKIE_PATH, secure=_secure(), httponly=True, samesite="lax"
    )
    return response


@router.get(
    "/sign-in",
    operation_id="startSignIn",
    status_code=status.HTTP_302_FOUND,
    response_class=RedirectResponse,
)
async def start_sign_in(
    auth: Auth, return_to: Annotated[str | None, Query(alias="returnTo")] = None
) -> Response:
    try:
        start = await auth.start_sign_in(return_to)
    except IdentityProviderUnavailableError:
        log.warning("sign_in_unavailable")
        return _refused(SignInRefusal.UNAVAILABLE)
    response = RedirectResponse(start.redirect_url, status_code=status.HTTP_302_FOUND)
    # SameSite=Lax: the cookie comes back with the top-level redirect from the Identity Provider.
    response.set_cookie(
        SIGN_IN_COOKIE,
        start.cookie,
        max_age=SIGN_IN_MAX_AGE_SECONDS,
        path=SIGN_IN_COOKIE_PATH,
        secure=_secure(),
        httponly=True,
        samesite="lax",
    )
    return response


@router.get(
    "/callback",
    operation_id="completeSignIn",
    status_code=status.HTTP_302_FOUND,
    response_class=RedirectResponse,
)
async def complete_sign_in(
    request: Request,
    auth: Auth,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> Response:
    try:
        result = await auth.complete_sign_in(
            code=code, state=state, error=error, cookie=request.cookies.get(SIGN_IN_COOKIE)
        )
    except SignInRefusedError as exc:
        return _refused(exc.reason)
    response = RedirectResponse(result.return_to, status_code=status.HTTP_302_FOUND)
    response.delete_cookie(
        SIGN_IN_COOKIE, path=SIGN_IN_COOKIE_PATH, secure=_secure(), httponly=True, samesite="lax"
    )
    response.set_cookie(
        SESSION_COOKIE,
        result.token,
        max_age=int(session_policy().absolute_timeout.total_seconds()),
        path="/",
        secure=_secure(),
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("", operation_id="getSession", response_model_by_alias=True)
async def get_session(user: User) -> UserAccount:
    return UserAccount.from_user(user)


@router.delete("", operation_id="deleteSession", response_model_by_alias=True)
async def delete_session(request: Request, response: Response, user: User, auth: Auth) -> SignOut:
    logout_url = await auth.sign_out(request.cookies.get(SESSION_COOKIE, ""))
    log.info("user_signed_out", extra={"user_id": str(user.user_id), "tenant_id": str(user.tenant_id)})
    response.delete_cookie(SESSION_COOKIE, path="/", secure=_secure(), httponly=True, samesite="lax")
    return SignOut(logout_url=logout_url or "/")


@router.post(BACKCHANNEL_LOGOUT_PATH.removeprefix("/v1/session"), operation_id="backchannelLogout")
async def backchannel_logout(auth: Auth, logout_token: Annotated[str, Form(max_length=16_384)]) -> Response:
    try:
        await auth.backchannel_logout(logout_token)
    except InvalidLogoutTokenError as exc:
        log.warning("backchannel_logout_refused")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid logout token.") from exc
    except IdentityProviderUnavailableError as exc:  # signing keys not readable: the provider may retry
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Sign-in service not reachable.") from exc
    return Response(status_code=status.HTTP_200_OK, headers={"Cache-Control": "no-store"})
