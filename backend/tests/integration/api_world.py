"""An API on a real PostgreSQL with one tenant, two members and a manager (SAPS-20 integration tests)."""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from saps.adapters.persistence.db import dispose_engines, session_factory
from saps.adapters.persistence.models import Invoice, Notification, UserAccount
from saps.api.deps import current_user, file_storage, job_queue
from saps.api.main import create_app
from saps.config import get_settings
from saps.domain.invoices import NotificationType
from saps.domain.users import CurrentUser
from tests.fakes import MemoryQueue, MemoryStorage
from tests.integration.db_urls import use_database
from tests.integration.pipeline import FIXTURES, World, new_world, process, rematch, uploaded

ORIGIN = "http://localhost:5173"
USER_HEADER = "X-Test-User"


@dataclass
class Api:
    client: AsyncClient
    app: FastAPI
    engine: AsyncEngine
    world: World
    storage: MemoryStorage
    queue: MemoryQueue
    users: dict[str, CurrentUser] = field(default_factory=dict)

    async def sample(self, relative: str, *, processed: bool = True) -> uuid.UUID:
        """An invoice of the world's tenant for a sample file, already through extraction and matching."""
        invoice_id = await uploaded(self.engine, FIXTURES / relative, self.world.tenant)
        if processed:
            await process(self.engine, invoice_id)
        return invoice_id

    async def rematch(self, invoice_id: uuid.UUID) -> None:
        """What the SAPS Worker does after `rematch_invoice`."""
        await rematch(self.engine, invoice_id)

    async def request(self, who: str, method: str, path: str, **kwargs: Any) -> Response:
        headers = {USER_HEADER: who, **kwargs.pop("headers", {})}
        return await self.client.request(method, path, headers=headers, **kwargs)

    async def get(self, invoice_id: uuid.UUID, who: str = "alice") -> dict[str, Any]:
        response = await self.request(who, "GET", f"/v1/invoices/{invoice_id}")
        assert response.status_code == 200, response.text
        body: dict[str, Any] = response.json()
        return body

    async def etag(self, invoice_id: uuid.UUID) -> str:
        response = await self.request("alice", "GET", f"/v1/invoices/{invoice_id}")
        return response.headers["etag"]

    async def claim(self, who: str, invoice_id: uuid.UUID) -> Response:
        return await self.request(who, "POST", f"/v1/invoices/{invoice_id}/claim")

    async def release(self, who: str, invoice_id: uuid.UUID) -> Response:
        return await self.request(who, "DELETE", f"/v1/invoices/{invoice_id}/claim")

    async def update(
        self, who: str, invoice_id: uuid.UUID, body: dict[str, Any], etag: str | None = None
    ) -> Response:
        headers = {"If-Match": etag or await self.etag(invoice_id)}
        return await self.request(who, "PATCH", f"/v1/invoices/{invoice_id}", json=body, headers=headers)

    async def resolve(self, who: str, invoice_id: uuid.UUID, etag: str | None = None) -> Response:
        headers = {"If-Match": etag or await self.etag(invoice_id)}
        return await self.request(who, "POST", f"/v1/invoices/{invoice_id}/resolution", headers=headers)

    async def reject(self, who: str, invoice_id: uuid.UUID, reason: str = "Not payable.") -> Response:
        return await self.request(
            who, "POST", f"/v1/invoices/{invoice_id}/rejection", json={"reason": reason}
        )

    async def confirm(self, who: str, invoice_id: uuid.UUID) -> Response:
        return await self.request(who, "POST", f"/v1/invoices/{invoice_id}/confirmation")

    async def decide(
        self, who: str, invoice_id: uuid.UUID, decision: str, comment: str | None = None
    ) -> Response:
        body: dict[str, Any] = {"decision": decision}
        if comment is not None:
            body["comment"] = comment
        return await self.request(who, "POST", f"/v1/invoices/{invoice_id}/approval", json=body)

    async def notifications(self, invoice_id: uuid.UUID) -> dict[str, list[NotificationType]]:
        """Notification types per recipient (display name), oldest first."""
        async with session_factory(self.engine)() as session:
            rows = await session.execute(
                select(UserAccount.display_name, Notification.type)
                .join(UserAccount, UserAccount.id == Notification.recipient_id)
                .where(Notification.invoice_id == invoice_id)
                .order_by(Notification.created_at)
            )
        result: dict[str, list[NotificationType]] = {}
        for name, kind in rows:
            result.setdefault(name, []).append(kind)
        return result

    async def storage_key(self, invoice_id: uuid.UUID) -> str:
        async with session_factory(self.engine)() as session:
            key = await session.scalar(select(Invoice.file_storage_key).where(Invoice.id == invoice_id))
        assert key is not None
        return key


@asynccontextmanager
async def make_api(
    engine: AsyncEngine, database_url: str, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[Api]:
    use_database(monkeypatch, database_url)
    monkeypatch.setenv("WEB_APP_ORIGIN", ORIGIN)
    get_settings.cache_clear()
    world = await new_world(engine)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers={"Origin": ORIGIN}) as client:
        api = Api(client, app, engine, world, MemoryStorage(), MemoryQueue())
        api.users = {
            "alice": world.alice,
            "bob": world.bob,
            "manager": world.manager,
            "manager2": world.manager2,
        }

        async def user_of_request(request: Request) -> CurrentUser:
            return api.users[request.headers[USER_HEADER]]  # per request, so claims can race

        app.dependency_overrides[current_user] = user_of_request
        app.dependency_overrides[file_storage] = lambda: api.storage
        app.dependency_overrides[job_queue] = lambda: api.queue
        try:
            yield api
        finally:
            await dispose_engines()
            get_settings.cache_clear()
