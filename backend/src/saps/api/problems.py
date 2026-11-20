"""RFC 9457 problem details for every error response (OpenAPI `Problem`)."""

import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_JSON = "application/problem+json"
log = logging.getLogger("saps.api")


def problem(
    status: int, detail: str | None = None, errors: list[dict[str, str]] | None = None
) -> JSONResponse:
    body: dict[str, Any] = {"type": "about:blank", "title": HTTPStatus(status).phrase, "status": status}
    if detail:
        body["detail"] = detail
    if errors:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


async def _http_exception(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    response = problem(exc.status_code, str(exc.detail) if exc.detail else None)
    if exc.headers:
        response.headers.update(exc.headers)
    return response


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    errors = [
        {"field": ".".join(str(part) for part in err["loc"][1:]), "message": str(err["msg"])}
        for err in exc.errors()
    ]
    return problem(HTTPStatus.BAD_REQUEST, "The request is not valid.", errors)


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Any other error: 500 problem+json without internal details; the details go to the log."""
    log.error("unhandled_error", exc_info=exc, extra={"path": request.url.path, "method": request.method})
    return problem(HTTPStatus.INTERNAL_SERVER_ERROR, "An unexpected error occurred. Please try again.")


def install_problem_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_exception)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unexpected_error)
