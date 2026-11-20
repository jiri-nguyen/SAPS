"""Integration: the S3 adapter against a real SeaweedFS (ADR-0006); skipped when Docker is not available."""

import io
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from saps.adapters.storage.s3_storage import S3FileStorage

pytestmark = pytest.mark.integration

S3_CONFIG = Path(__file__).parents[3] / "deploy" / "seaweedfs" / "s3.json"
ACCESS, SECRET = "local-test-access", "local-test-secret"


@pytest.fixture(scope="module")
def endpoint() -> Iterator[str]:
    core = pytest.importorskip("testcontainers.core.container")
    container = (
        core.DockerContainer("chrislusf/seaweedfs:4.53")
        .with_command("server -dir=/data -s3 -s3.config=/etc/seaweedfs/s3.json -ip.bind=0.0.0.0")
        .with_volume_mapping(str(S3_CONFIG), "/etc/seaweedfs/s3.json", "ro")
        .with_exposed_ports(8333)
    )
    try:
        container.start()
    except Exception as exc:  # Docker not running
        pytest.skip(f"Docker not available: {exc}")
    try:
        url = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8333)}"
        probe = S3FileStorage(endpoint_url=url, bucket="probe", access_key=ACCESS, secret_key=SECRET)
        deadline = time.monotonic() + 60
        while True:  # SeaweedFS needs a few seconds before the S3 API answers
            try:
                probe._client.list_buckets()
                break
            except Exception:
                if time.monotonic() > deadline:
                    raise
                time.sleep(1)
        yield url
    finally:
        container.stop()


async def test_put_stores_the_file_in_a_new_bucket(endpoint: str) -> None:
    storage = S3FileStorage(
        endpoint_url=endpoint, bucket="invoices-test", access_key=ACCESS, secret_key=SECRET
    )
    await storage.put(
        "invoices/1/a", io.BytesIO(b"%PDF-first"), "application/pdf"
    )  # SeaweedFS creates the bucket
    await storage.put("invoices/1/b", io.BytesIO(b"%PDF-second"), "application/pdf")
    assert storage.read("invoices/1/a") == b"%PDF-first"
    assert storage.read("invoices/1/b") == b"%PDF-second"
    head = storage._client.head_object(Bucket="invoices-test", Key="invoices/1/a")
    assert head["ContentType"] == "application/pdf"


async def test_storage_errors_are_raised(endpoint: str) -> None:
    wrong = "wrong-secret"
    storage = S3FileStorage(
        endpoint_url=endpoint, bucket="invoices-test", access_key=ACCESS, secret_key=wrong
    )
    with pytest.raises(Exception, match=r"SignatureDoesNotMatch|AccessDenied|InvalidAccessKeyId|403"):
        await storage.put("invoices/1/c", io.BytesIO(b"%PDF-x"), "application/pdf")


async def test_get_streams_the_object_in_chunks(endpoint: str) -> None:  # SAPS-20 downloadInvoiceFile
    storage = S3FileStorage(
        endpoint_url=endpoint, bucket="invoices-test", access_key=ACCESS, secret_key=SECRET
    )
    content = b"%PDF-" + b"0123456789" * 60_000  # about 600 KB: more than one 256 KB chunk
    await storage.put("invoices/2/big", io.BytesIO(content), "application/pdf")
    chunks = [chunk async for chunk in storage.get("invoices/2/big")]
    assert len(chunks) > 1 and b"".join(chunks) == content


async def test_get_reports_a_missing_object(endpoint: str) -> None:
    storage = S3FileStorage(
        endpoint_url=endpoint, bucket="invoices-test", access_key=ACCESS, secret_key=SECRET
    )
    with pytest.raises(FileNotFoundError):
        [chunk async for chunk in storage.get("invoices/2/does-not-exist")]
