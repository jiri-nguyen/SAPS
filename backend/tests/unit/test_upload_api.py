"""SAPS-17 HTTP layer: uploadInvoice and getInvoice with in-memory ports (no database)."""

from collections.abc import AsyncIterator, Iterator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from saps.api.deps import current_user, invoice_reader, upload_service
from saps.api.main import create_app
from saps.application.upload import UploadInvoiceService
from saps.config import get_settings
from saps.domain.users import CurrentUser, Role
from tests.fakes import NOW, PDF_BYTES, MemoryInvoices, MemoryQueue, MemoryStorage

ORIGIN = "http://localhost:5173"
MB = 1024 * 1024
MEMBER = CurrentUser(uuid4(), uuid4(), "member1", "Accounting Member 1", Role.ACCOUNTING_MEMBER)


class Ports:
    def __init__(self) -> None:
        self.repo = MemoryInvoices()
        self.storage = MemoryStorage()
        self.queue = MemoryQueue()


@pytest.fixture
def ports() -> Ports:
    return Ports()


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, ports: Ports) -> Iterator[FastAPI]:
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "1")
    monkeypatch.setenv("WEB_APP_ORIGIN", ORIGIN)
    get_settings.cache_clear()
    application = create_app()

    async def service() -> UploadInvoiceService:
        return UploadInvoiceService(ports.repo, ports.repo, ports.storage, ports.queue, lambda: NOW, MB)

    async def reader() -> MemoryInvoices:
        return ports.repo

    application.dependency_overrides[current_user] = lambda: MEMBER
    application.dependency_overrides[upload_service] = service
    application.dependency_overrides[invoice_reader] = reader
    yield application
    get_settings.cache_clear()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test", headers={"Origin": ORIGIN}) as c:
        yield c


async def _upload(
    client: AsyncClient, content: bytes = PDF_BYTES, key: str | None = "key-1", name: str = "inv.pdf"
):
    headers = {"Idempotency-Key": key} if key is not None else {}
    return await client.post(
        "/v1/invoices", files={"file": (name, content, "application/pdf")}, headers=headers
    )


async def test_upload_returns_202_with_the_invoice(client: AsyncClient, ports: Ports) -> None:
    response = await _upload(client)
    assert response.status_code == 202
    body = response.json()
    assert response.headers["location"] == f"/v1/invoices/{body['id']}"
    assert body["status"] == "UPLOADED" and body["currency"] == "USD"
    assert body["file"]["contentType"] == "application/pdf" and body["file"]["sizeBytes"] == len(PDF_BYTES)
    assert body["uploadedBy"] == {"id": str(MEMBER.user_id), "displayName": "Accounting Member 1"}
    assert body["lines"] == [] and body["exceptions"] == [] and body["approval"] is None
    assert [str(i) for i in ports.queue.sent] == [body["id"]]


async def test_same_key_returns_the_same_invoice(client: AsyncClient, ports: Ports) -> None:
    first = await _upload(client)
    second = await _upload(client)
    assert second.status_code == 202 and second.json()["id"] == first.json()["id"]
    assert len(ports.storage.objects) == 1


@pytest.mark.parametrize(
    ("content", "key", "status", "detail"),
    [
        (PDF_BYTES, None, 400, "The request is not valid."),
        (PDF_BYTES, "k" * 65, 400, "The request is not valid."),
        (b"", "key-1", 400, "The file is empty."),
        (b"just text, named .pdf", "key-1", 415, "Only PDF, JPEG and PNG files are accepted."),
        (b"%PDF-" + b"0" * MB, "key-1", 413, "The file is larger than 1 MB."),
    ],
)
async def test_invalid_uploads_are_problems(
    client: AsyncClient, ports: Ports, content: bytes, key: str | None, status: int, detail: str
) -> None:
    response = await _upload(client, content, key)
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == detail
    assert ports.storage.objects == {} and ports.repo.uploads == {}


async def test_missing_key_names_the_header(client: AsyncClient) -> None:
    response = await _upload(client, key=None)
    assert response.json()["errors"][0]["field"] == "Idempotency-Key"


async def test_chunked_body_above_the_limit_is_stopped(client: AsyncClient, ports: Ports) -> None:  # EC-01
    boundary = "saps-test-boundary"

    async def body() -> AsyncIterator[bytes]:
        yield (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="big.pdf"\r\n'
            "Content-Type: application/pdf\r\n\r\n%PDF-"
        ).encode()
        for _ in range(3):
            yield b"0" * MB
        yield f"\r\n--{boundary}--\r\n".encode()

    response = await client.post(
        "/v1/invoices",
        content=body(),
        headers={"Idempotency-Key": "key-1", "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "The file is larger than 1 MB."
    assert ports.repo.uploads == {}


async def test_manager_cannot_upload_and_origin_is_required(app: FastAPI, client: AsyncClient) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as no_origin:
        assert (await _upload(no_origin)).status_code == 403  # type: ignore[arg-type]
    app.dependency_overrides[current_user] = lambda: CurrentUser(
        uuid4(), MEMBER.tenant_id, "manager1", "Accounting Manager 1", Role.ACCOUNTING_MANAGER
    )
    response = await _upload(client)
    assert response.status_code == 403
    assert response.json()["detail"] == "Your role is not allowed for this operation."


async def test_storage_failure_is_a_500_problem(client: AsyncClient, ports: Ports) -> None:  # EC-07
    ports.storage.fail = True
    response = await _upload(client)
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert ports.repo.uploads == {}


async def test_message_failure_still_returns_202(client: AsyncClient, ports: Ports) -> None:  # EC-06
    ports.queue.fail = True
    response = await _upload(client)
    assert response.status_code == 202
    assert ports.repo.uploads


async def test_get_invoice_returns_it_with_an_etag(client: AsyncClient) -> None:
    created = (await _upload(client)).json()
    response = await client.get(f"/v1/invoices/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.headers["etag"] == f'W/"{int(NOW.timestamp() * 1_000_000)}"'


async def test_unknown_or_invalid_invoice_id(client: AsyncClient) -> None:
    missing = await client.get(f"/v1/invoices/{uuid4()}")
    assert missing.status_code == 404 and missing.json()["detail"] == "Invoice not found."
    assert (await client.get("/v1/invoices/not-a-uuid")).status_code == 400


def test_real_storage_and_queue_are_built_from_settings() -> None:
    from saps.adapters.queue.dramatiq_queue import DramatiqJobQueue
    from saps.adapters.storage.s3_storage import S3FileStorage
    from saps.api.deps import file_storage, job_queue

    file_storage.cache_clear()
    job_queue.cache_clear()
    assert isinstance(file_storage(), S3FileStorage)
    assert isinstance(job_queue(), DramatiqJobQueue)
