"""The mail intake tick of the SAPS Worker (SAPS-45, ADR-0012); the timer is `worker/timer.py`.

Every process ticks. Per company mailbox a PostgreSQL advisory lock lets one process read it at a time
(BR-08, EC-11).
A tick never raises: a failed mailbox is logged and tried again at the next tick (EC-08).
"""

import logging
from datetime import UTC, datetime
from functools import lru_cache

from saps.adapters.mail.imap_mailbox import ImapMailbox
from saps.adapters.persistence.db import get_engine, session_factory
from saps.adapters.persistence.inbound_mail_repository import SqlInboundMailRepository
from saps.adapters.persistence.invoice_repository import SqlInvoiceRepository
from saps.adapters.storage.s3_storage import S3FileStorage
from saps.application.mail_intake import MailIntakeService
from saps.application.upload import UploadInvoiceService
from saps.config import Settings
from saps.ports.file_storage import FileStoragePort
from saps.ports.inbound_mail import MailboxOwner
from saps.ports.job_queue import JobQueuePort
from saps.ports.mailbox import MailboxPort, MailboxUnavailableError

log = logging.getLogger("saps.worker.mail_intake")


def build_mailbox(settings: Settings) -> MailboxPort:
    """Selected by MAIL_ADAPTER (ADR-0001 style); `graph` for Outlook comes with SAPS-53."""
    if settings.mail_adapter == "imap":
        return ImapMailbox(
            settings.imap_host,
            settings.imap_port,
            ssl=settings.imap_ssl,
            password=settings.imap_password.get_secret_value(),
        )
    raise ValueError(f"Unknown MAIL_ADAPTER: {settings.mail_adapter}")


@lru_cache
def _storage(endpoint: str, bucket: str, access_key: str, secret_key: str) -> FileStoragePort:
    return S3FileStorage(endpoint_url=endpoint, bucket=bucket, access_key=access_key, secret_key=secret_key)


def _utc_now() -> datetime:
    return datetime.now(UTC)


async def run_mail_intake(settings: Settings, queue: JobQueuePort, mailbox: MailboxPort) -> None:
    """One tick over the mailboxes of all active companies."""
    try:
        engine = get_engine(settings.app_database_url)  # `saps_app`: row-level security applies (SAPS-41)
        records = SqlInboundMailRepository(engine)
        owners = await records.list_mailboxes()
    except Exception:
        log.exception("mail_poll_failed", extra={"stage": "list_mailboxes"})
        return
    storage = _storage(
        settings.s3_endpoint_url,
        settings.s3_bucket,
        settings.s3_access_key,
        settings.s3_secret_key.get_secret_value(),
    )
    for owner in owners:
        try:
            async with records.try_lock_mailbox(owner.mailbox_address) as got:
                if not got:  # another process reads this mailbox now
                    continue
                await _poll(settings, owner, records, mailbox, storage, queue)
        except MailboxUnavailableError as exc:
            log.warning(
                "mail_poll_failed",
                extra={
                    "tenant_id": str(owner.tenant_id),
                    "mailbox": owner.mailbox_address,
                    "error": str(exc),
                },
            )
        except Exception:
            log.exception("mail_poll_failed", extra={"tenant_id": str(owner.tenant_id)})


async def _poll(
    settings: Settings,
    owner: MailboxOwner,
    records: SqlInboundMailRepository,
    mailbox: MailboxPort,
    storage: FileStoragePort,
    queue: JobQueuePort,
) -> None:
    invoices = SqlInvoiceRepository(session_factory(get_engine(settings.app_database_url), owner.tenant_id))
    uploads = UploadInvoiceService(
        invoices, invoices, storage, queue, _utc_now, settings.max_upload_size_mb * 1024 * 1024
    )
    service = MailIntakeService(mailbox, records, uploads, _utc_now, settings.mail_batch_size)
    await service.poll_mailbox(owner)
