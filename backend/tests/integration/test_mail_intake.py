"""Integration: invoice intake from company mailboxes, GreenMail and PostgreSQL (SAPS-45 TS-03 to TS-07)."""

import asyncio
import imaplib
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from saps.adapters.persistence.db import dispose_engines, session_factory
from saps.adapters.persistence.inbound_mail_repository import SqlInboundMailRepository
from saps.adapters.persistence.invoice_repository import SqlInvoiceRepository
from saps.adapters.persistence.models import InboundMail, Invoice, InvoiceEvent, MatchingSettings, Tenant
from saps.application.mail_intake import MailIntakeService
from saps.application.upload import UploadInvoiceService
from saps.config import get_settings
from saps.domain.invoices import InvoiceStatus
from saps.domain.mail_intake import InboundMailStatus, IntakeChannel, SkipReason
from saps.ports.inbound_mail import MailboxOwner
from saps.ports.mailbox import MailboxUnavailableError, MailRef
from saps.worker import mail_intake as worker
from tests.fakes import MemoryQueue, MemoryStorage
from tests.integration.api_world import Api
from tests.integration.db_urls import use_database
from tests.integration.mail_server import PASSWORD, MailServer
from tests.integration.pipeline import FIXTURES

pytestmark = pytest.mark.integration

DS01 = (FIXTURES / "ds-01/invoices/ds-01-trade-po.pdf").read_bytes()
DS03 = (FIXTURES / "ds-03/invoices/ds-03-above-threshold.pdf").read_bytes()


async def _company(engine: AsyncEngine) -> MailboxOwner:
    suffix = uuid.uuid4().hex[:8]
    async with session_factory(engine)() as session, session.begin():
        tenant = Tenant(
            name=f"Mail company {suffix}",
            code=f"m{suffix}",
            mailbox_address=f"ap-{suffix}@example.com",
            email_domain=f"{suffix}.example.com",
            keycloak_group=f"/companies/m{suffix}",
        )
        session.add(tenant)
        await session.flush()
        session.add(MatchingSettings(tenant_id=tenant.id))
        return MailboxOwner(tenant.id, tenant.name, tenant.mailbox_address or "")


class World:
    """The intake service on the real database, with the real IMAP adapter and in-memory storage and queue."""

    def __init__(self, app_engine: AsyncEngine, server: MailServer, mailbox: object | None = None) -> None:
        self.engine, self.server = app_engine, server
        self.storage, self.queue = MemoryStorage(), MemoryQueue()
        self.records = SqlInboundMailRepository(app_engine)
        self.mailbox = mailbox or server.mailbox()

    def service(self, owner: MailboxOwner) -> MailIntakeService:
        invoices = SqlInvoiceRepository(session_factory(self.engine, owner.tenant_id))
        uploads = UploadInvoiceService(
            invoices, invoices, self.storage, self.queue, lambda: datetime.now(UTC), 10 * 1024 * 1024
        )
        return MailIntakeService(self.mailbox, self.records, uploads, lambda: datetime.now(UTC), 50)  # type: ignore[arg-type]


@pytest.fixture
async def world(app_engine: AsyncEngine, mail_server: MailServer) -> World:
    return World(app_engine, mail_server)


def _folder(server: MailServer, address: str, folder: str) -> int:
    """Number of mails in an IMAP folder of a mailbox (0 when it does not exist)."""
    client = imaplib.IMAP4(server.host, server.imap_port)
    try:
        client.login(address, PASSWORD)
        status, data = client.select(folder, readonly=True)
        return int(data[0]) if status == "OK" else 0
    finally:
        client.logout()


async def _invoices(engine: AsyncEngine, tenant_id: uuid.UUID) -> list[Invoice]:
    async with session_factory(engine, tenant_id)() as session:
        rows = await session.execute(
            select(Invoice).where(Invoice.tenant_id == tenant_id).order_by(Invoice.created_at)
        )
        return list(rows.scalars())


# TS-03 / BR-01, BR-03, BR-04, EC-01 -------------------------------------------------------------------------


async def test_a_mail_with_two_pdfs_becomes_two_uploaded_invoices_of_that_company(
    world: World, mail_server: MailServer, engine: AsyncEngine, app_engine: AsyncEngine
) -> None:
    owner = await _company(engine)
    other = await _company(engine)
    message_id = mail_server.send(
        owner.mailbox_address, subject="Invoices March", attachments={"a.pdf": DS01, "b.pdf": DS03}
    )

    result = await world.service(owner).poll_mailbox(owner)

    assert (result.imported, result.invoices, result.failed) == (1, 2, False)
    invoices = await _invoices(app_engine, owner.tenant_id)
    assert len(invoices) == 2 and await _invoices(app_engine, other.tenant_id) == []
    assert {i.status for i in invoices} == {InvoiceStatus.UPLOADED}
    assert {(i.channel, i.uploaded_by) for i in invoices} == {(IntakeChannel.MAIL, None)}
    assert {i.file_name for i in invoices} == {"a.pdf", "b.pdf"} and {
        i.inbound_mail_id for i in invoices
    } != {None}
    assert set(world.queue.tenant_of.values()) == {owner.tenant_id} and len(world.queue.sent) == 2
    assert len(world.storage.objects) == 2

    async with session_factory(app_engine, owner.tenant_id)() as session:
        record = (
            await session.execute(select(InboundMail).where(InboundMail.mail_key == message_id))
        ).scalar_one()
        events = (
            (await session.execute(select(InvoiceEvent).where(InvoiceEvent.action == "UPLOAD")))
            .scalars()
            .all()
        )
    assert (record.status, record.subject, record.sender) == (
        InboundMailStatus.PROCESSED,
        "Invoices March",
        "Vendor Ltd <billing@vendor.example.net>",
    )
    assert [a["skipReason"] for a in record.attachments] == [None, None]
    assert {e.actor for e in events} == {"mail"}
    assert all(e.details and e.details["channel"] == "MAIL" for e in events)

    assert _folder(mail_server, owner.mailbox_address, "INBOX") == 0
    assert _folder(mail_server, owner.mailbox_address, "Processed") == 1


# TS-04 / BR-06, EC-02 ---------------------------------------------------------------------------------------


async def test_a_mail_without_a_valid_attachment_is_skipped_and_moved(
    world: World, mail_server: MailServer, engine: AsyncEngine, app_engine: AsyncEngine
) -> None:
    owner = await _company(engine)
    key = mail_server.send(owner.mailbox_address, subject="Hello")
    mail_server.send(owner.mailbox_address, attachments={"notes.txt": b"just notes"})

    result = await world.service(owner).poll_mailbox(owner)

    assert (result.imported, result.skipped, result.invoices) == (0, 2, 0)
    assert await _invoices(app_engine, owner.tenant_id) == []
    async with session_factory(app_engine, owner.tenant_id)() as session:
        record = (await session.execute(select(InboundMail).where(InboundMail.mail_key == key))).scalar_one()
    assert (record.status, record.skip_reason) == (
        InboundMailStatus.SKIPPED,
        SkipReason.NO_VALID_ATTACHMENT.value,
    )
    assert _folder(mail_server, owner.mailbox_address, "Skipped") == 2
    assert _folder(mail_server, owner.mailbox_address, "INBOX") == 0 and not world.queue.sent


# TS-05 / BR-05, BR-08, EC-06, EC-07, EC-11 ------------------------------------------------------------------


class MoveFails:
    """The real mailbox, except that moving a mail fails: the crash between import and move (EC-07)."""

    def __init__(self, inner: object) -> None:
        self._inner = inner

    async def list_new(self, mailbox: str, limit: int) -> list[MailRef]:
        return await self._inner.list_new(mailbox, limit)  # type: ignore[attr-defined, no-any-return]

    async def read(self, mailbox: str, ref: MailRef) -> object:
        return await self._inner.read(mailbox, ref)  # type: ignore[attr-defined, no-any-return]

    async def move(self, mailbox: str, ref: MailRef, folder: str) -> None:
        raise MailboxUnavailableError("move refused")


async def test_a_crash_between_import_and_move_creates_no_second_invoice(
    app_engine: AsyncEngine, mail_server: MailServer, engine: AsyncEngine
) -> None:
    owner = await _company(engine)
    mail_server.send(owner.mailbox_address, attachments={"a.pdf": DS01})
    crashing = World(app_engine, mail_server, MoveFails(mail_server.mailbox()))
    first = await crashing.service(owner).poll_mailbox(owner)
    assert first.invoices == 1 and _folder(mail_server, owner.mailbox_address, "INBOX") == 1

    healthy = World(app_engine, mail_server)
    healthy.storage, healthy.queue = crashing.storage, crashing.queue
    again = await healthy.service(owner).poll_mailbox(owner)

    assert (again.invoices, again.imported) == (0, 0)  # the record was final: only the move is repeated
    assert len(await _invoices(app_engine, owner.tenant_id)) == 1 and len(crashing.queue.sent) == 1
    assert _folder(mail_server, owner.mailbox_address, "INBOX") == 0
    assert _folder(mail_server, owner.mailbox_address, "Processed") == 1


async def test_a_mail_left_received_is_finished_without_duplicates(
    world: World, mail_server: MailServer, engine: AsyncEngine, app_engine: AsyncEngine
) -> None:  # EC-06: the process died after the first attachment, before the record was finished
    owner = await _company(engine)
    key = mail_server.send(owner.mailbox_address, attachments={"a.pdf": DS01, "b.pdf": DS03})
    service = world.service(owner)
    ref = (await world.mailbox.list_new(owner.mailbox_address, 5))[0]  # type: ignore[attr-defined]
    mail = await world.mailbox.read(owner.mailbox_address, ref)  # type: ignore[attr-defined]
    record = await world.records.find_or_create(
        owner, mail_key=key, sender="s", subject="s", received_at=mail.received_at
    )
    from saps.application.upload import UploadSource

    await service._attachment(UploadSource.of_mail(owner.tenant_id, record.id), mail, mail.attachments[0])
    assert len(await _invoices(app_engine, owner.tenant_id)) == 1

    result = await service.poll_mailbox(owner)

    assert result.invoices == 2  # the first one is returned by its idempotency key, the second is new
    assert len(await _invoices(app_engine, owner.tenant_id)) == 2
    assert len(set(world.queue.sent)) == len(world.queue.sent) == 2  # no invoice queued twice
    assert _folder(mail_server, owner.mailbox_address, "Processed") == 1


async def test_only_one_process_reads_a_mailbox_at_a_time(app_engine: AsyncEngine) -> None:
    records = SqlInboundMailRepository(app_engine)
    address = f"lock-{uuid.uuid4().hex[:6]}@example.com"
    async with records.try_lock_mailbox(address) as first:
        async with records.try_lock_mailbox(address) as second:
            async with records.try_lock_mailbox("other-" + address) as other:
                assert (first, second, other) == (True, False, True)
    async with records.try_lock_mailbox(address) as again:  # released with the first holder
        assert again is True


async def test_two_ticks_at_the_same_time_import_a_mail_once(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
    mail_server: MailServer,
    engine: AsyncEngine,
    app_engine: AsyncEngine,
) -> None:
    use_database(monkeypatch, database_url)
    monkeypatch.setenv("IMAP_HOST", mail_server.host)
    monkeypatch.setenv("IMAP_PORT", str(mail_server.imap_port))
    monkeypatch.setenv("IMAP_PASSWORD", PASSWORD)
    monkeypatch.setenv("MAIL_ADAPTER", "imap")
    storage, queue = MemoryStorage(), MemoryQueue()
    monkeypatch.setattr(worker, "_storage", lambda *args: storage)
    settings = get_settings()
    owner = await _company(engine)
    mail_server.send(owner.mailbox_address, attachments={"a.pdf": DS01})
    mailbox = worker.build_mailbox(settings)
    try:
        await asyncio.gather(*(worker.run_mail_intake(settings, queue, mailbox) for _ in range(3)))
        assert len(await _invoices(app_engine, owner.tenant_id)) == 1 and len(queue.sent) == 1
        assert _folder(mail_server, owner.mailbox_address, "Processed") == 1
    finally:
        await dispose_engines()
        get_settings.cache_clear()


async def test_an_unreachable_mail_server_does_not_stop_the_tick(
    database_url: str, monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine, caplog: pytest.LogCaptureFixture
) -> None:  # EC-08
    use_database(monkeypatch, database_url)
    monkeypatch.setenv("IMAP_HOST", "127.0.0.1")
    monkeypatch.setenv("IMAP_PORT", "1")  # nothing listens here
    monkeypatch.setenv("MAIL_ADAPTER", "imap")
    settings = get_settings()
    await _company(engine)
    try:
        await worker.run_mail_intake(settings, MemoryQueue(), worker.build_mailbox(settings))
    finally:
        await dispose_engines()
        get_settings.cache_clear()
    assert "mail_poll_failed" in caplog.text


# TS-06 / BR-01, EC-13, EC-14 --------------------------------------------------------------------------------


async def test_the_same_mail_in_two_company_mailboxes_gives_one_invoice_in_each(
    world: World, mail_server: MailServer, engine: AsyncEngine, app_engine: AsyncEngine
) -> None:
    first, second = await _company(engine), await _company(engine)
    key = mail_server.send([first.mailbox_address, second.mailbox_address], attachments={"a.pdf": DS01})

    for owner in (first, second):
        assert (await world.service(owner).poll_mailbox(owner)).invoices == 1

    for owner, foreign in ((first, second), (second, first)):
        assert len(await _invoices(app_engine, owner.tenant_id)) == 1
        async with session_factory(app_engine, owner.tenant_id)() as session:  # row-level security
            seen = (
                (await session.execute(select(InboundMail.tenant_id).where(InboundMail.mail_key == key)))
                .scalars()
                .all()
            )
        assert seen == [owner.tenant_id] and foreign.tenant_id not in seen
    async with session_factory(app_engine)() as session:  # no company: nothing is visible
        assert (await session.execute(text("SELECT count(*) FROM inbound_mail"))).scalar_one() == 0


async def test_only_active_companies_with_a_mailbox_are_read(
    engine: AsyncEngine, app_engine: AsyncEngine
) -> None:
    active = await _company(engine)
    inactive = await _company(engine)
    async with session_factory(engine)() as session, session.begin():
        tenant = await session.get_one(Tenant, inactive.tenant_id)
        tenant.is_active = False
    listed = {o.tenant_id for o in await SqlInboundMailRepository(app_engine).list_mailboxes()}
    assert active.tenant_id in listed and inactive.tenant_id not in listed


# TS-07 / BR-04 ----------------------------------------------------------------------------------------------


async def test_the_api_shows_where_a_mail_invoice_came_from(api: Api, engine: AsyncEngine) -> None:
    tenant_id = api.world.tenant[0]
    owner = MailboxOwner(tenant_id, "Company", "ap@api.example.com")
    records = SqlInboundMailRepository(engine)
    record = await records.find_or_create(
        owner,
        mail_key="<api@vendor.example.net>",
        sender="Vendor <v@example.net>",
        subject="March invoice",
        received_at=datetime(2027, 3, 1, 2, 30, tzinfo=UTC),
    )
    invoices = SqlInvoiceRepository(session_factory(engine, tenant_id))
    uploads = UploadInvoiceService(
        invoices, invoices, MemoryStorage(), MemoryQueue(), lambda: datetime.now(UTC), 10**7
    )
    import hashlib
    import io

    from saps.application.upload import IncomingFile, UploadSource

    incoming = IncomingFile("m.pdf", len(DS01), hashlib.sha256(DS01).hexdigest(), DS01[:8], io.BytesIO(DS01))
    created = await uploads.upload(UploadSource.of_mail(tenant_id, record.id), "mail:api:1", incoming)

    body = await api.get(created.invoice.id)
    assert body["uploadedBy"] is None
    assert body["source"] == {
        "channel": "MAIL",
        "mailFrom": "Vendor <v@example.net>",
        "mailSubject": "March invoice",
        "mailReceivedAt": "2027-03-01T02:30:00Z",
    }
    uploaded = await api.sample("ds-03/invoices/ds-03-above-threshold.pdf", processed=False)
    assert (await api.get(uploaded))["source"] == {
        "channel": "UPLOAD",
        "mailFrom": None,
        "mailSubject": None,
        "mailReceivedAt": None,
    }


async def test_two_processes_creating_the_record_of_one_mail_get_the_same_record(
    engine: AsyncEngine, app_engine: AsyncEngine
) -> None:  # the unique key lets one win; both continue with the same record
    owner = await _company(engine)
    records = SqlInboundMailRepository(app_engine)
    args = {
        "mail_key": "<race@vendor.example.net>",
        "sender": "s",
        "subject": "s",
        "received_at": datetime.now(UTC),
    }
    found = await asyncio.gather(*(records.find_or_create(owner, **args) for _ in range(4)))
    assert len({r.id for r in found}) == 1 and found[0].status is InboundMailStatus.RECEIVED
    again = await records.find_or_create(owner, **args)  # an existing record is returned as it is
    assert again.id == found[0].id
