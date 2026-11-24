"""Persistence port of the inbound mail records (SAPS-45 BR-05)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from saps.domain.mail_intake import AttachmentResult, InboundMailStatus, SkipReason


@dataclass(frozen=True)
class MailboxOwner:
    """A company whose mailbox is read (BR-01, EC-14)."""

    tenant_id: UUID
    name: str
    mailbox_address: str


@dataclass(frozen=True)
class InboundMailRecord:
    id: UUID
    status: InboundMailStatus


class InboundMailRepository(Protocol):
    async def list_mailboxes(self) -> list[MailboxOwner]:
        """Active companies with a mailbox address."""
        ...

    async def find_or_create(
        self,
        owner: MailboxOwner,
        *,
        mail_key: str,
        sender: str,
        subject: str,
        received_at: datetime,
    ) -> InboundMailRecord:
        """The record of the mail in this company; created as RECEIVED when new."""
        ...

    async def find(self, owner: MailboxOwner, mail_key: str) -> InboundMailRecord | None: ...

    async def finish(
        self,
        owner: MailboxOwner,
        record_id: UUID,
        *,
        status: InboundMailStatus,
        skip_reason: SkipReason | None,
        results: Sequence[AttachmentResult],
        processed_at: datetime,
    ) -> None: ...
