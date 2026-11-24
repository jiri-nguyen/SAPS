"""Invoice intake from company mailboxes (SAPS-45, ADR-0012).

Each attachment goes through the upload use case, so a mail invoice follows exactly the path of an upload. A
record per mail and an idempotency key per attachment make the import exactly-once: a crash at any point loses
no mail and creates no second invoice (BR-05).
"""

import hashlib
import io
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from saps.application.upload import IncomingFile, UploadInvoiceService, UploadSource
from saps.domain.invoice_files import HEADER_BYTES, FileRejectedError
from saps.domain.mail_intake import (
    MAX_SENDER,
    MAX_SUBJECT,
    AttachmentResult,
    InboundMailStatus,
    clip,
    final_status,
    mail_idempotency_key,
    overall_skip_reason,
    skip_reason_of,
)
from saps.ports.inbound_mail import InboundMailRepository, MailboxOwner
from saps.ports.mailbox import PROCESSED_FOLDER, SKIPPED_FOLDER, Attachment, Mail, MailboxPort, MailRef

log = logging.getLogger("saps.mail_intake")


@dataclass(frozen=True)
class PollResult:
    imported: int = 0  # mails with at least one invoice
    skipped: int = 0  # mails without a valid attachment
    invoices: int = 0
    failed: bool = False  # a mail could not be imported; the rest of the mailbox waits for the next tick


def _digest(mail_key: str) -> str:
    """Logs hold a hash of the mail key, never mail content (spec §3.7)."""
    return hashlib.sha256(mail_key.encode()).hexdigest()[:12]


class MailIntakeService:
    def __init__(
        self,
        mailbox: MailboxPort,
        records: InboundMailRepository,
        uploads: UploadInvoiceService,
        clock: Callable[[], datetime],
        batch_size: int,
    ) -> None:
        self._mailbox = mailbox
        self._records = records
        self._uploads = uploads
        self._clock = clock
        self._batch_size = batch_size

    async def poll_mailbox(self, owner: MailboxOwner) -> PollResult:
        """Raises `MailboxUnavailableError` when the mail server cannot be used (EC-08)."""
        refs = await self._mailbox.list_new(owner.mailbox_address, self._batch_size)
        imported = skipped = invoices = 0
        for ref in refs:
            try:
                results = await self._import(owner, ref)
            except Exception:  # EC-09: the mail stays in the inbox, RECEIVED; the next tick tries again
                log.exception(
                    "mail_import_failed",
                    extra={"tenant_id": str(owner.tenant_id), "mail": _digest(ref.mail_key)},
                )
                return PollResult(imported, skipped, invoices, failed=True)
            if results is None:
                continue
            count = sum(r.invoice_id is not None for r in results)
            invoices += count
            if count:
                imported += 1
            else:
                skipped += 1
        return PollResult(imported, skipped, invoices)

    async def _import(self, owner: MailboxOwner, ref: MailRef) -> list[AttachmentResult] | None:
        known = await self._records.find(owner, ref.mail_key)
        if known is not None and known.status is not InboundMailStatus.RECEIVED:
            # Only the move failed last time (EC-07): nothing to import again.
            await self._move(owner, ref, known.status)
            return None

        mail = await self._mailbox.read(owner.mailbox_address, ref)
        record = await self._records.find_or_create(
            owner,
            mail_key=ref.mail_key,
            sender=clip(mail.sender, MAX_SENDER),
            subject=clip(mail.subject, MAX_SUBJECT),
            received_at=mail.received_at,
        )
        source = UploadSource.of_mail(owner.tenant_id, record.id)
        results = [await self._attachment(source, mail, a) for a in mail.attachments]
        status = final_status(results)
        await self._records.finish(
            owner,
            record.id,
            status=status,
            skip_reason=overall_skip_reason(results),
            results=results,
            processed_at=self._clock(),
        )
        extra = {"tenant_id": str(owner.tenant_id), "mail": _digest(ref.mail_key)}
        invoices = sum(r.invoice_id is not None for r in results)
        if status is InboundMailStatus.PROCESSED:
            log.info(
                "mail_imported",
                extra={**extra, "invoices": invoices, "skipped_attachments": len(results) - invoices},
            )
        else:
            log.info(
                "mail_skipped",
                extra={**extra, "reason": overall_skip_reason(results), "attachments": len(results)},
            )
        await self._move(owner, ref, status)
        return results

    async def _attachment(self, source: UploadSource, mail: Mail, attachment: Attachment) -> AttachmentResult:
        data = attachment.data
        incoming = IncomingFile(
            attachment.name,
            len(data),
            hashlib.sha256(data).hexdigest(),
            data[:HEADER_BYTES],
            io.BytesIO(data),
        )
        key = mail_idempotency_key(mail.ref.mail_key, attachment.position)
        try:
            result = await self._uploads.upload(source, key, incoming)
        except FileRejectedError as exc:  # BR-07: the other attachments go on
            return AttachmentResult(
                attachment.position, attachment.name or "", len(data), skip_reason=skip_reason_of(exc)
            )
        return AttachmentResult(
            attachment.position, attachment.name or "", len(data), invoice_id=result.invoice.id
        )

    async def _move(self, owner: MailboxOwner, ref: MailRef, status: InboundMailStatus) -> None:
        folder = PROCESSED_FOLDER if status is InboundMailStatus.PROCESSED else SKIPPED_FOLDER
        try:
            await self._mailbox.move(owner.mailbox_address, ref, folder)
        except Exception:  # EC-07: the record is final; the next tick moves the mail again
            log.warning(
                "mail_move_failed",
                extra={"tenant_id": str(owner.tenant_id), "mail": _digest(ref.mail_key), "folder": folder},
            )
