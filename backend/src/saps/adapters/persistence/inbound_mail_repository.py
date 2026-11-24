"""SQL implementation of the inbound mail port (SAPS-45): one short transaction of one company per call."""

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from saps.adapters.persistence.db import session_factory
from saps.adapters.persistence.models import InboundMail, Tenant
from saps.domain.mail_intake import AttachmentResult, InboundMailStatus, SkipReason
from saps.ports.inbound_mail import InboundMailRecord, MailboxOwner

MAIL_LOCK_KEY = (
    3700045  # first key of the advisory lock per mailbox; the second is the hash of the address (BR-08)
)
INTAKE_ACTOR = "mail"


class SqlInboundMailRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def list_mailboxes(self) -> list[MailboxOwner]:
        """The tenant table has no row-level security: every active company with a mailbox (EC-14)."""
        async with session_factory(self._engine)() as session:
            rows = await session.execute(
                select(Tenant.id, Tenant.name, Tenant.mailbox_address)
                .where(Tenant.is_active, Tenant.mailbox_address.is_not(None))
                .order_by(Tenant.code)
            )
            return [MailboxOwner(r.id, r.name, r.mailbox_address) for r in rows if r.mailbox_address]

    @asynccontextmanager
    async def try_lock_mailbox(self, address: str) -> AsyncIterator[bool]:
        """One SAPS Worker process reads a mailbox at a time (EC-11). The lock lives on its own connection and
        ends with it, also when the process dies; yields False when another process holds it."""
        async with self._engine.connect() as conn:
            got = bool(
                await conn.scalar(
                    text("SELECT pg_try_advisory_lock(:k, hashtext(:a))"), {"k": MAIL_LOCK_KEY, "a": address}
                )
            )
            try:
                yield got
            finally:
                if got:
                    await conn.scalar(
                        text("SELECT pg_advisory_unlock(:k, hashtext(:a))"),
                        {"k": MAIL_LOCK_KEY, "a": address},
                    )

    async def find(self, owner: MailboxOwner, mail_key: str) -> InboundMailRecord | None:
        async with session_factory(self._engine, owner.tenant_id)() as session:
            row = await session.scalar(
                select(InboundMail).where(
                    InboundMail.tenant_id == owner.tenant_id, InboundMail.mail_key == mail_key
                )
            )
            return None if row is None else InboundMailRecord(row.id, row.status)

    async def find_or_create(
        self,
        owner: MailboxOwner,
        *,
        mail_key: str,
        sender: str,
        subject: str,
        received_at: datetime,
    ) -> InboundMailRecord:
        existing = await self.find(owner, mail_key)
        if existing is not None:
            return existing
        record_id = uuid4()
        try:
            async with session_factory(self._engine, owner.tenant_id)() as session, session.begin():
                session.add(
                    InboundMail(
                        id=record_id,
                        tenant_id=owner.tenant_id,
                        mailbox_address=owner.mailbox_address,
                        mail_key=mail_key,
                        sender=sender,
                        subject=subject,
                        received_at=received_at,
                        status=InboundMailStatus.RECEIVED,
                        created_by=INTAKE_ACTOR,
                        updated_by=INTAKE_ACTOR,
                    )
                )
        except IntegrityError:  # another process created it meanwhile
            winner = await self.find(owner, mail_key)
            if winner is None:  # pragma: no cover - the unique key guarantees a winner
                raise
            return winner
        return InboundMailRecord(record_id, InboundMailStatus.RECEIVED)

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
        async with session_factory(self._engine, owner.tenant_id)() as session, session.begin():
            row = await session.get_one(InboundMail, record_id)
            row.status = status
            row.skip_reason = skip_reason.value if skip_reason else None
            row.attachments = [_attachment_json(r) for r in results]
            row.processed_at = processed_at
            row.updated_by = INTAKE_ACTOR
            row.updated_at = func.now()


def _attachment_json(result: AttachmentResult) -> dict[str, object]:
    return {
        "position": result.position,
        "name": result.name,
        "sizeBytes": result.size_bytes,
        "invoiceId": str(result.invoice_id) if result.invoice_id else None,
        "skipReason": result.skip_reason.value if result.skip_reason else None,
    }
