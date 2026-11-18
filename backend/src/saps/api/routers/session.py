"""Session operations: createSession, getSession, deleteSession (SAPS-27, ADR-0008)."""

import logging

from fastapi import APIRouter, HTTPException, Request, Response, status

from saps.api.deps import SESSION_COOKIE, Auth, User, session_policy
from saps.api.schemas import SessionCreate, UserAccount
from saps.application.auth import InvalidCredentialsError
from saps.config import get_settings

router = APIRouter(prefix="/v1/session", tags=["Session"])
log = logging.getLogger("saps.api.session")


@router.post("", operation_id="createSession", response_model_by_alias=True)
async def create_session(body: SessionCreate, response: Response, auth: Auth) -> UserAccount:
    try:
        result = await auth.sign_in(body.username, body.password)
    except InvalidCredentialsError as exc:
        log.info("sign_in_failed", extra={"username": body.username})
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password.") from exc
    response.set_cookie(
        SESSION_COOKIE,
        result.token,
        max_age=int(session_policy().absolute_timeout.total_seconds()),
        path="/",
        secure=get_settings().session_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    log.info(
        "user_signed_in", extra={"user_id": str(result.user.user_id), "tenant_id": str(result.user.tenant_id)}
    )
    return UserAccount.from_user(result.user)


@router.get("", operation_id="getSession", response_model_by_alias=True)
async def get_session(user: User) -> UserAccount:
    return UserAccount.from_user(user)


@router.delete("", operation_id="deleteSession", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(request: Request, user: User, auth: Auth) -> Response:
    token = request.cookies.get(SESSION_COOKIE, "")
    await auth.sign_out(token)
    log.info("user_signed_out", extra={"user_id": str(user.user_id), "tenant_id": str(user.tenant_id)})
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=get_settings().session_cookie_secure, httponly=True, samesite="lax"
    )
    return response
