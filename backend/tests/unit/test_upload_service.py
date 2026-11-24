"""SAPS-17 upload use case with in-memory ports."""

import io
from dataclasses import replace
from uuid import uuid4

import pytest

from saps.application.upload import IncomingFile, UploadInvoiceService, UploadSource
from saps.domain.invoice_files import UnsupportedFileTypeError
from saps.domain.mail_intake import IntakeChannel
from saps.domain.users import CurrentUser, Role
from saps.ports.invoices import NewUpload
from tests.fakes import NOW, PDF_BYTES, MemoryInvoices, MemoryQueue, MemoryStorage

USER = CurrentUser(uuid4(), uuid4(), "member1", "Accounting Member 1", Role.ACCOUNTING_MEMBER)
SHA = "c" * 64


def _file(content: bytes = PDF_BYTES, name: str = "inv.pdf") -> IncomingFile:
    return IncomingFile(name, len(content), SHA, content[:8], io.BytesIO(content))


def _service(
    repo: MemoryInvoices, storage: MemoryStorage | None = None, queue: MemoryQueue | None = None
) -> UploadInvoiceService:
    return UploadInvoiceService(
        repo, repo, storage or MemoryStorage(), queue or MemoryQueue(), lambda: NOW, 1024
    )


async def test_upload_stores_the_file_creates_the_invoice_and_queues_it() -> None:
    repo, storage, queue = MemoryInvoices(), MemoryStorage(), MemoryQueue()
    result = await _service(repo, storage, queue).upload(UploadSource.of_user(USER), "key-1", _file())
    assert result.created and result.queued
    upload = repo.uploads[result.invoice.id]
    assert upload.storage_key == f"tenants/{USER.tenant_id}/invoices/{result.invoice.id}/{SHA}"
    assert storage.objects[upload.storage_key] == (PDF_BYTES, "application/pdf")
    assert (upload.actor, upload.uploaded_by, upload.uploaded_at) == ("member1", USER.user_id, NOW)
    assert upload.file.name == "inv.pdf" and upload.file.size_bytes == len(PDF_BYTES)
    assert queue.sent == [result.invoice.id]


async def test_same_key_returns_the_first_invoice_without_storing_again() -> None:  # BR-06, EC-03
    repo, storage, queue = MemoryInvoices(), MemoryStorage(), MemoryQueue()
    first = await _service(repo, storage, queue).upload(UploadSource.of_user(USER), "key-1", _file())
    second = await _service(repo, storage, queue).upload(
        UploadSource.of_user(USER), "key-1", _file(b"not even checked")
    )
    assert second.invoice.id == first.invoice.id and not second.created
    assert len(storage.objects) == 1 and len(queue.sent) == 1


async def test_same_key_in_another_tenant_is_a_new_invoice() -> None:
    repo = MemoryInvoices()
    first = await _service(repo).upload(UploadSource.of_user(USER), "key-1", _file())
    other = await _service(repo).upload(
        UploadSource.of_user(replace(USER, tenant_id=uuid4())), "key-1", _file()
    )
    assert other.created and other.invoice.id != first.invoice.id


async def test_parallel_request_with_the_same_key_returns_the_winner() -> None:  # EC-04
    repo, queue = MemoryInvoices(), MemoryQueue()
    winner = await _service(MemoryInvoices()).upload(UploadSource.of_user(USER), "key-1", _file())
    winner_upload = NewUpload(
        winner.invoice.id, USER.tenant_id, USER.user_id, "member1", winner.invoice.file, "k", "key-1", NOW
    )
    repo.race_winner = winner_upload
    result = await _service(repo, queue=queue).upload(UploadSource.of_user(USER), "key-1", _file())
    assert result.invoice.id == winner.invoice.id and not result.created
    assert queue.sent == []


async def test_rejected_file_is_neither_stored_nor_saved() -> None:
    repo, storage = MemoryInvoices(), MemoryStorage()
    with pytest.raises(UnsupportedFileTypeError):
        await _service(repo, storage).upload(
            UploadSource.of_user(USER), "key-1", _file(b"plain text", "fake.pdf")
        )
    assert storage.objects == {} and repo.uploads == {}


async def test_storage_failure_saves_nothing() -> None:  # EC-07
    repo = MemoryInvoices()
    with pytest.raises(OSError, match="unavailable"):
        await _service(repo, MemoryStorage(fail=True)).upload(UploadSource.of_user(USER), "key-1", _file())
    assert repo.uploads == {}


async def test_message_failure_still_accepts_the_upload() -> None:  # EC-06
    repo = MemoryInvoices()
    result = await _service(repo, queue=MemoryQueue(fail=True)).upload(
        UploadSource.of_user(USER), "key-1", _file()
    )
    assert result.created and not result.queued
    assert result.invoice.id in repo.uploads


async def test_a_mail_attachment_is_an_invoice_without_a_user() -> None:  # SAPS-45 BR-03, BR-04
    repo, queue = MemoryInvoices(), MemoryQueue()
    tenant, mail_id = uuid4(), uuid4()
    source = UploadSource.of_mail(tenant, mail_id)
    result = await _service(repo, queue=queue).upload(source, "mail:abc:1", _file())
    upload = repo.uploads[result.invoice.id]
    assert (upload.actor, upload.uploaded_by, upload.channel, upload.inbound_mail_id) == (
        "mail",
        None,
        IntakeChannel.MAIL,
        mail_id,
    )
    assert result.invoice.uploaded_by is None and result.invoice.source.channel is IntakeChannel.MAIL
    assert queue.tenant_of[result.invoice.id] == tenant
    again = await _service(repo, queue=queue).upload(source, "mail:abc:1", _file())  # a retry after a crash
    assert not again.created and again.invoice.id == result.invoice.id
