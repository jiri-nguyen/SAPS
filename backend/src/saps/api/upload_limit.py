"""Size guard for invoice uploads (SAPS-17 EC-01): stop reading the body once it is too large.

Pure ASGI middleware: a declared Content-Length above the limit is refused before any byte is read; a body
without one (chunked) is counted while it is received. The exact file size is checked again after parsing.
"""

import json

from fastapi import HTTPException, status
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MULTIPART_OVERHEAD_BYTES = 64 * 1024  # boundaries and part headers around the file


class UploadSizeLimitMiddleware:
    def __init__(self, app: ASGIApp, *, path: str, max_file_bytes: int) -> None:
        self.app = app
        self.path = path
        self.max_body_bytes = max_file_bytes + MULTIPART_OVERHEAD_BYTES
        self.detail = f"The file is larger than {max_file_bytes // (1024 * 1024)} MB."

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not (scope["type"] == "http" and scope["method"] == "POST" and scope["path"] == self.path):
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_body_bytes:
            await self._too_large(send)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, self.detail)
            return message

        await self.app(scope, limited_receive, send)

    async def _too_large(self, send: Send) -> None:
        body = json.dumps(
            {"type": "about:blank", "title": "Content Too Large", "status": 413, "detail": self.detail}
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/problem+json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
