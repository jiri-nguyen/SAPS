"""The upload size guard as plain ASGI (SAPS-17 EC-01)."""

from collections.abc import Awaitable, Callable

import pytest
from fastapi import HTTPException
from starlette.types import Message, Receive, Scope, Send

from saps.api.upload_limit import MULTIPART_OVERHEAD_BYTES, UploadSizeLimitMiddleware

LIMIT = 1000


def _scope(path: str = "/v1/invoices", method: str = "POST", length: int | None = None) -> Scope:
    headers = [(b"content-length", str(length).encode())] if length is not None else []
    return {"type": "http", "method": method, "path": path, "headers": headers}


def _receive(*chunks: bytes) -> Receive:
    messages = [
        {"type": "http.request", "body": c, "more_body": i < len(chunks) - 1} for i, c in enumerate(chunks)
    ]

    async def receive() -> Message:
        return messages.pop(0)

    return receive


class Recorder:
    def __init__(self) -> None:
        self.messages: list[Message] = []

    async def __call__(self, message: Message) -> None:
        self.messages.append(message)


def _reading_app(calls: list[str]) -> Callable[[Scope, Receive, Send], Awaitable[None]]:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        calls.append("called")
        while (await receive()).get("more_body"):
            pass

    return app


async def test_declared_length_above_the_limit_is_refused_before_reading() -> None:
    calls: list[str] = []
    send = Recorder()
    middleware = UploadSizeLimitMiddleware(_reading_app(calls), path="/v1/invoices", max_file_bytes=LIMIT)
    await middleware(_scope(length=LIMIT + MULTIPART_OVERHEAD_BYTES + 1), _receive(b""), send)
    assert calls == []
    assert send.messages[0]["status"] == 413


async def test_counted_body_above_the_limit_raises_413() -> None:
    middleware = UploadSizeLimitMiddleware(_reading_app([]), path="/v1/invoices", max_file_bytes=LIMIT)
    chunk = b"0" * (LIMIT + MULTIPART_OVERHEAD_BYTES)
    with pytest.raises(HTTPException) as caught:
        await middleware(_scope(), _receive(chunk, b"0"), Recorder())
    assert caught.value.status_code == 413


@pytest.mark.parametrize("scope", [_scope(path="/v1/session"), _scope(method="GET"), _scope(length=10)])
async def test_other_requests_pass(scope: Scope) -> None:
    calls: list[str] = []
    middleware = UploadSizeLimitMiddleware(_reading_app(calls), path="/v1/invoices", max_file_bytes=LIMIT)
    await middleware(scope, _receive(b"0" * 10), Recorder())
    assert calls == ["called"]
