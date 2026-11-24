"""Integration: uploadInvoice and getInvoice on a real PostgreSQL (SAPS-17 TS-01, TS-03, TS-04)."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from saps.adapters.persistence.db import dispose_engines, session_factory
from saps.adapters.persistence.models import (
    Approval,
    Invoice,
    InvoiceEvent,
    InvoiceException,
    InvoiceLine,
    UserAccount,
)
from saps.api.deps import current_user, file_storage, job_queue
from saps.api.main import create_app
from saps.config import get_settings
from saps.domain.invoices import ApprovalDecision, ExceptionCode, ExceptionStatus, InvoiceStatus
from saps.domain.users import CurrentUser
from saps.seed import _run as run_seed
from tests.fakes import JPEG_BYTES, PDF_BYTES, PNG_BYTES, MemoryQueue, MemoryStorage
from tests.integration.db_urls import use_database

pytestmark = pytest.mark.integration

ORIGIN = "http://localhost:5173"


class Stack:
    def __init__(self, app: FastAPI, client: AsyncClient, engine: AsyncEngine, member: CurrentUser) -> None:
        self.app, self.client, self.engine, self.member = app, client, engine, member
        self.storage = MemoryStorage()
        self.queue = MemoryQueue()


@pytest.fixture
async def stack(database_url: str, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Stack]:
    await run_seed(database_url, "upload-test-pw")
    use_database(monkeypatch, database_url)
    monkeypatch.setenv("WEB_APP_ORIGIN", ORIGIN)
    get_settings.cache_clear()
    engine = create_async_engine(database_url)
    async with session_factory(engine)() as session:
        user = (
            await session.execute(select(UserAccount).where(UserAccount.username == "member1"))
        ).scalar_one()
        member = CurrentUser(user.id, user.tenant_id, user.username, user.display_name, user.role)
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers={"Origin": ORIGIN}
    ) as c:
        s = Stack(app, c, engine, member)
        app.dependency_overrides[current_user] = lambda: s.member
        app.dependency_overrides[file_storage] = lambda: s.storage
        app.dependency_overrides[job_queue] = lambda: s.queue
        try:
            yield s
        finally:
            await dispose_engines()
            await engine.dispose()
            get_settings.cache_clear()


async def _upload(stack: Stack, content: bytes, key: str, name: str = "inv.pdf"):
    return await stack.client.post(
        "/v1/invoices",
        files={"file": (name, content, "application/octet-stream")},
        headers={"Idempotency-Key": key},
    )


async def _count(stack: Stack, key: str) -> int | None:
    async with session_factory(stack.engine)() as session:
        return await session.scalar(
            select(func.count()).select_from(Invoice).where(Invoice.idempotency_key == key)
        )


@pytest.mark.parametrize(
    ("content", "name", "content_type"),
    [
        (PDF_BYTES, "a.pdf", "application/pdf"),
        (JPEG_BYTES, "b.jpg", "image/jpeg"),
        (PNG_BYTES, "c.png", "image/png"),
    ],
)
async def test_upload_creates_the_invoice_event_object_and_message(
    stack: Stack, content: bytes, name: str, content_type: str
) -> None:  # TS-01
    response = await _upload(stack, content, uuid.uuid4().hex, name)
    assert response.status_code == 202
    invoice_id = uuid.UUID(response.json()["id"])
    async with session_factory(stack.engine)() as session:
        invoice = await session.get_one(Invoice, invoice_id)
        event = await session.scalar(select(InvoiceEvent).where(InvoiceEvent.invoice_id == invoice_id))
    assert invoice.status is InvoiceStatus.UPLOADED and invoice.file_content_type == content_type
    assert invoice.file_name == name and invoice.created_by == "member1"
    assert (
        invoice.file_storage_key == f"tenants/{invoice.tenant_id}/invoices/{invoice_id}/{invoice.file_sha256}"
    )
    assert stack.storage.objects[invoice.file_storage_key] == (content, content_type)
    assert event is not None and (event.action, event.actor, event.status_to) == (
        "UPLOAD",
        "member1",
        "UPLOADED",
    )
    assert event.details == {"fileName": name, "sizeBytes": len(content), "sha256": invoice.file_sha256}
    assert stack.queue.sent == [invoice_id]


async def test_same_key_sequential_and_parallel_gives_one_invoice(stack: Stack) -> None:  # TS-03
    key = uuid.uuid4().hex
    first, second = await _upload(stack, PDF_BYTES, key), await _upload(stack, PDF_BYTES, key)
    assert first.json()["id"] == second.json()["id"] and await _count(stack, key) == 1

    key = uuid.uuid4().hex
    responses = await asyncio.gather(*(_upload(stack, PDF_BYTES, key) for _ in range(3)))
    assert {r.status_code for r in responses} == {202}
    assert len({r.json()["id"] for r in responses}) == 1
    assert await _count(stack, key) == 1


async def test_same_file_with_two_keys_gives_two_invoices(stack: Stack) -> None:  # TS-04, BR-07
    first = await _upload(stack, PDF_BYTES, uuid.uuid4().hex)
    second = await _upload(stack, PDF_BYTES, uuid.uuid4().hex)
    assert first.json()["id"] != second.json()["id"]
    assert first.json()["file"]["sha256"] == second.json()["file"]["sha256"]


async def test_get_invoice_returns_lines_exceptions_and_approval(stack: Stack) -> None:
    invoice_id = uuid.UUID((await _upload(stack, PDF_BYTES, uuid.uuid4().hex)).json()["id"])
    now = datetime.now(UTC)
    async with session_factory(stack.engine)() as session, session.begin():
        manager = (
            await session.execute(select(UserAccount).where(UserAccount.username == "manager1"))
        ).scalar_one()
        tenant = stack.member.tenant_id
        line = InvoiceLine(
            tenant_id=tenant, invoice_id=invoice_id, line_number=1, po_number="0100001", po_line_number=1,
            quantity=Decimal("2.000"), unit_price=Decimal("10.5000"),
        )  # fmt: skip
        session.add(line)
        await session.flush()
        session.add_all(
            [
                InvoiceException(
                    tenant_id=tenant,
                    invoice_id=invoice_id,
                    invoice_line_id=line.id,
                    code=ExceptionCode.EX6,
                    message="m",
                    status=ExceptionStatus.RESOLVED,
                    resolved_by=stack.member.user_id,
                    resolved_at=now,
                ),
                Approval(
                    tenant_id=tenant,
                    invoice_id=invoice_id,
                    decided_by=manager.id,
                    decision=ApprovalDecision.APPROVED,
                    decided_at=now,
                ),
            ]
        )
        (await session.get_one(Invoice, invoice_id)).assigned_to = stack.member.user_id

    response = await stack.client.get(f"/v1/invoices/{invoice_id}")
    body = response.json()
    assert response.status_code == 200 and response.headers["etag"].startswith('W/"')
    assert body["lines"][0]["quantity"] == "2.000" and body["lines"][0]["unitPrice"] == "10.5000"
    assert body["lines"][0]["matchStatus"] == "NOT_MATCHED"
    assert body["exceptions"][0]["resolvedBy"]["displayName"] == "Accounting Member 1"
    assert body["approval"]["decidedBy"]["displayName"] == "Accounting Manager 1"
    assert body["assignedTo"]["displayName"] == "Accounting Member 1"


async def test_invoice_of_another_tenant_is_not_found(stack: Stack) -> None:  # ADR-0007
    invoice_id = (await _upload(stack, PDF_BYTES, uuid.uuid4().hex)).json()["id"]
    stack.app.dependency_overrides[current_user] = lambda: CurrentUser(
        stack.member.user_id, uuid.uuid4(), "member1", "Accounting Member 1", stack.member.role
    )
    assert (await stack.client.get(f"/v1/invoices/{invoice_id}")).status_code == 404
