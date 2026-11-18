"""CSRF protection: state-changing requests must come from the SAPS Web App origin.

ADR-0008, SAPS-27 BR-06.
"""

import json

from starlette.types import ASGIApp, Receive, Scope, Send

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class OriginCheckMiddleware:
    """Pure ASGI middleware, so it runs before routing and before any request body is read."""

    def __init__(self, app: ASGIApp, allowed_origin: str) -> None:
        self.app = app
        self.allowed_origin = allowed_origin.rstrip("/")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] in UNSAFE_METHODS:
            headers = dict(scope["headers"])
            origin = headers.get(b"origin", b"").decode("latin-1").rstrip("/")
            if origin != self.allowed_origin:
                await self._forbid(send)
                return
        await self.app(scope, receive, send)

    @staticmethod
    async def _forbid(send: Send) -> None:
        body = json.dumps(
            {
                "type": "about:blank",
                "title": "Forbidden",
                "status": 403,
                "detail": "The request origin is not allowed.",
            }
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 403,
                "headers": [
                    (b"content-type", b"application/problem+json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
