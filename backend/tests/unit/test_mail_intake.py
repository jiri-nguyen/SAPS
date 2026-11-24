"""Mail intake use case with in-memory ports (SAPS-45 TS-01, TS-02)."""

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from saps.application.mail_intake import MailIntakeService
from saps.application.upload import UploadInvoiceService
from saps.domain.mail_intake import (
    AttachmentResult,
    InboundMailStatus,
    SkipReason,
    mail_idempotency_key,
)
from saps.ports.inbound_mail import InboundMailRecord, MailboxOwner
from saps.ports.mailbox import Attachment, Mail, MailboxUnavailableError, MailRef
from tests.fakes import NOW, PDF_BYTES, MemoryInvoices, MemoryQueue, MemoryStorage

OWNER = MailboxOwner(uuid4(), "Demo Vietnam", "ap@vn.example.com")
PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 20


def _mail(key: str, *attachments: tuple[str, bytes]) -> Mail:
    return Mail(
        ref=MailRef(key, f"uid-{key}"),
        sender="vendor@example.net",
        subject=f"Invoice {key}",
        received_at=NOW,
        attachments=[
            Attachment(i, name, "application/octet-stream", data)
            for i, (name, data) in enumerate(attachments, 1)
        ],
    )


class FakeMailbox:
    def __init__(self, *mails: Mail) -> None:
        self.inbox = {m.ref.mail_key: m for m in mails}
        self.moved: dict[str, list[str]] = {}
        self.read_keys: list[str] = []
        self.fail_list: Exception | None = None
        self.fail_move = False

    async def list_new(self, mailbox: str, limit: int) -> list[MailRef]:
        if self.fail_list:
            raise self.fail_list
        return [m.ref for m in list(self.inbox.values())[:limit]]

    async def read(self, mailbox: str, ref: MailRef) -> Mail:
        self.read_keys.append(ref.mail_key)
        return self.inbox[ref.mail_key]

    async def move(self, mailbox: str, ref: MailRef, folder: str) -> None:
        if self.fail_move:
            raise MailboxUnavailableError("move refused")
        self.moved.setdefault(folder, []).append(ref.mail_key)
        self.inbox.pop(ref.mail_key, None)


class FakeRecords:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}

    async def list_mailboxes(self) -> list[MailboxOwner]:
        return [OWNER]

    async def find(self, owner: MailboxOwner, mail_key: str) -> InboundMailRecord | None:
        row = self.rows.get(mail_key)
        return None if row is None else InboundMailRecord(row["id"], row["status"])  # type: ignore[arg-type]

    async def find_or_create(
        self, owner: MailboxOwner, *, mail_key: str, sender: str, subject: str, received_at: datetime
    ) -> InboundMailRecord:
        row = self.rows.setdefault(
            mail_key,
            {"id": uuid4(), "status": InboundMailStatus.RECEIVED, "sender": sender, "subject": subject},
        )
        return InboundMailRecord(row["id"], row["status"])  # type: ignore[arg-type]

    async def finish(
        self,
        owner: MailboxOwner,
        record_id: UUID,
        *,
        status: InboundMailStatus,
        skip_reason: SkipReason | None,
        results: Sequence[AttachmentResult],
        processed_at: datetime,
    ) -> None:
        row = next(r for r in self.rows.values() if r["id"] == record_id)
        row.update(status=status, skip_reason=skip_reason, results=list(results))


class World:
    def __init__(self, *mails: Mail, storage: MemoryStorage | None = None) -> None:
        self.mailbox, self.records = FakeMailbox(*mails), FakeRecords()
        self.invoices, self.queue = MemoryInvoices(), MemoryQueue()
        uploads = UploadInvoiceService(
            self.invoices, self.invoices, storage or MemoryStorage(), self.queue, lambda: NOW, 1024
        )
        self.service = MailIntakeService(self.mailbox, self.records, uploads, lambda: datetime.now(UTC), 50)


async def test_a_mail_with_two_attachments_becomes_two_invoices_of_the_company() -> None:  # EC-01
    world = World(_mail("m1", ("a.pdf", PDF_BYTES), ("b.png", PNG)))
    result = await world.service.poll_mailbox(OWNER)
    assert (result.imported, result.skipped, result.invoices, result.failed) == (1, 0, 2, False)
    uploads = list(world.invoices.uploads.values())
    assert {u.tenant_id for u in uploads} == {OWNER.tenant_id}
    assert {u.channel.value for u in uploads} == {"MAIL"} and {u.uploaded_by for u in uploads} == {None}
    assert sorted(u.idempotency_key for u in uploads) == sorted(mail_idempotency_key("m1", i) for i in (1, 2))
    assert world.records.rows["m1"]["status"] is InboundMailStatus.PROCESSED
    assert world.mailbox.moved == {"Processed": ["m1"]}
    assert len(world.queue.tenant_of) == 2


@pytest.mark.parametrize(
    ("attachments", "reason"),
    [
        ((), SkipReason.NO_VALID_ATTACHMENT),
        ((("notes.docx", b"PK\x03\x04 not an invoice"),), SkipReason.NO_VALID_ATTACHMENT),
        ((("fake.pdf", b"plain text"),), SkipReason.NO_VALID_ATTACHMENT),
        ((("empty.pdf", b""),), SkipReason.NO_VALID_ATTACHMENT),
        ((("big.pdf", PDF_BYTES + b"0" * 2000),), SkipReason.NO_VALID_ATTACHMENT),
    ],
)
async def test_a_mail_without_a_valid_attachment_is_skipped(
    attachments: tuple[tuple[str, bytes], ...], reason: SkipReason, caplog: pytest.LogCaptureFixture
) -> None:  # EC-02, EC-03
    world = World(_mail("m1", *attachments))
    with caplog.at_level(logging.INFO):
        result = await world.service.poll_mailbox(OWNER)
    assert (result.imported, result.skipped, result.invoices) == (0, 1, 0)
    assert world.records.rows["m1"]["status"] is InboundMailStatus.SKIPPED
    assert world.records.rows["m1"]["skip_reason"] == reason
    assert world.mailbox.moved == {"Skipped": ["m1"]} and not world.invoices.uploads
    assert "mail_skipped" in caplog.text


async def test_each_rejected_attachment_gets_its_own_reason_and_the_others_go_on() -> None:  # BR-07
    world = World(
        _mail(
            "m1", ("a.pdf", PDF_BYTES), ("b.pdf", b""), ("c.pdf", b"text"), ("d.pdf", PDF_BYTES + b"0" * 2000)
        )
    )
    await world.service.poll_mailbox(OWNER)
    results = world.records.rows["m1"]["results"]
    assert [(r.position, r.invoice_id is not None, r.skip_reason) for r in results] == [  # type: ignore[attr-defined]
        (1, True, None),
        (2, False, SkipReason.EMPTY),
        (3, False, SkipReason.UNSUPPORTED_TYPE),
        (4, False, SkipReason.TOO_LARGE),
    ]
    assert world.records.rows["m1"]["status"] is InboundMailStatus.PROCESSED


async def test_a_mail_that_was_final_but_not_moved_is_only_moved_again() -> None:  # EC-07
    world = World(_mail("m1", ("a.pdf", PDF_BYTES)))
    world.mailbox.fail_move = True
    first = await world.service.poll_mailbox(OWNER)
    assert first.invoices == 1 and "m1" in world.mailbox.inbox and not world.mailbox.moved
    world.mailbox.fail_move = False
    again = await world.service.poll_mailbox(OWNER)
    assert (again.invoices, again.imported) == (0, 0)  # nothing imported twice
    assert len(world.invoices.uploads) == 1 and world.mailbox.moved == {"Processed": ["m1"]}
    assert world.mailbox.read_keys == ["m1"]  # the second tick did not even read the mail


async def test_a_failure_halfway_leaves_the_mail_received_and_the_retry_creates_no_duplicate(
    caplog: pytest.LogCaptureFixture,
) -> None:  # EC-06, EC-09
    storage = MemoryStorage()
    world = World(_mail("m1", ("a.pdf", PDF_BYTES), ("b.png", PNG)), storage=storage)
    real_put = storage.put
    calls = 0

    async def flaky_put(key: str, data: object, content_type: str) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:  # the second attachment cannot be stored
            raise ConnectionError("SAPS File Storage unavailable")
        await real_put(key, data, content_type)  # type: ignore[arg-type]

    storage.put = flaky_put  # type: ignore[method-assign]
    with caplog.at_level(logging.ERROR):
        failed = await world.service.poll_mailbox(OWNER)
    assert failed.failed and "mail_import_failed" in caplog.text
    assert world.records.rows["m1"]["status"] is InboundMailStatus.RECEIVED
    assert "m1" in world.mailbox.inbox and len(world.invoices.uploads) == 1

    retry = await world.service.poll_mailbox(OWNER)
    assert not retry.failed and retry.invoices == 2
    assert len(world.invoices.uploads) == 2  # the first attachment was not imported twice
    assert world.mailbox.moved == {"Processed": ["m1"]}


async def test_a_failing_mail_stops_the_mailbox_for_this_tick() -> None:
    world = World(_mail("m1", ("a.pdf", PDF_BYTES)), _mail("m2", ("b.pdf", PDF_BYTES)))
    world.mailbox.read = _raise  # type: ignore[method-assign]
    result = await world.service.poll_mailbox(OWNER)
    assert result.failed and not world.mailbox.moved


async def _raise(*_: object) -> Mail:
    raise ConnectionError("mail server went away")


async def test_an_unreachable_mail_server_raises_to_the_caller() -> None:  # EC-08
    world = World()
    world.mailbox.fail_list = MailboxUnavailableError("refused")
    with pytest.raises(MailboxUnavailableError):
        await world.service.poll_mailbox(OWNER)


async def test_sender_and_subject_are_stored_shortened() -> None:
    mail = _mail("m1", ("a.pdf", PDF_BYTES))
    long = Mail(mail.ref, "s" * 400, "t" * 700, mail.received_at, mail.attachments)
    world = World(long)
    await world.service.poll_mailbox(OWNER)
    assert (len(world.records.rows["m1"]["sender"]), len(world.records.rows["m1"]["subject"])) == (320, 500)  # type: ignore[arg-type]
