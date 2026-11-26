"""SQL implementations of the processing calendar ports (SAPS-52)."""

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from saps.adapters.persistence.db import session_factory
from saps.adapters.persistence.models import (
    Invoice,
    InvoiceEvent,
    ProcessingCalendarRule,
    Tenant,
    UserAccount,
)
from saps.domain.invoices import InvoiceStatus
from saps.domain.processing_calendar import CalendarRule
from saps.ports.invoice_hold import HeldInvoice
from saps.ports.processing_calendar import CalendarSnapshot, CalendarView, Company

HOLD_RELEASE_LOCK_KEY = 3700052  # advisory lock of the release timer, shared by all SAPS Worker processes
RELEASE_HOLD_ACTION = "RELEASE_HOLD"
SYSTEM_ACTOR = "system"


def _rule(row: ProcessingCalendarRule) -> CalendarRule:
    return CalendarRule(
        kind=row.kind,
        from_day=row.from_day,
        to_day=row.to_day,
        weekday=row.weekday,
        day=row.day,
        label=row.label,
    )


async def _rules(session: AsyncSession, tenant_id: UUID) -> list[ProcessingCalendarRule]:
    rows = await session.execute(
        select(ProcessingCalendarRule)
        .where(ProcessingCalendarRule.tenant_id == tenant_id)
        .order_by(ProcessingCalendarRule.position)
    )
    return list(rows.scalars())


async def calendar_snapshot(session: AsyncSession, tenant_id: UUID) -> CalendarSnapshot:
    """The rules and the time zone of a company, read in the caller's transaction."""
    zone = await session.scalar(select(Tenant.time_zone).where(Tenant.id == tenant_id))
    return CalendarSnapshot(tuple(_rule(r) for r in await _rules(session, tenant_id)), zone or "UTC")


class SqlProcessingCalendarRepository:
    """Runs in the request's transaction (the Accounting Manager's change applies at once, BR-07)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, tenant_id: UUID) -> CalendarView:
        snapshot = await calendar_snapshot(self._session, tenant_id)
        latest = (
            await self._session.execute(
                select(ProcessingCalendarRule.updated_at, ProcessingCalendarRule.updated_by)
                .where(ProcessingCalendarRule.tenant_id == tenant_id)
                .order_by(ProcessingCalendarRule.updated_at.desc())
                .limit(1)
            )
        ).first()
        if latest is None:
            return CalendarView(snapshot.rules, snapshot.time_zone, None, None)
        name = await self._session.scalar(
            select(UserAccount.display_name).where(
                UserAccount.tenant_id == tenant_id, UserAccount.username == latest.updated_by
            )
        )
        return CalendarView(snapshot.rules, snapshot.time_zone, latest.updated_at, name or latest.updated_by)

    async def replace(self, tenant_id: UUID, rules: Sequence[CalendarRule], actor: str) -> None:
        await self._session.execute(
            delete(ProcessingCalendarRule).where(ProcessingCalendarRule.tenant_id == tenant_id)
        )
        self._session.add_all(
            ProcessingCalendarRule(
                tenant_id=tenant_id,
                position=index,
                kind=rule.kind,
                from_day=rule.from_day,
                to_day=rule.to_day,
                weekday=rule.weekday,
                day=rule.day,
                label=(rule.label or None),
                created_by=actor,
                updated_by=actor,
            )
            for index, rule in enumerate(rules)
        )
        await self._session.flush()


class SqlHeldInvoiceRepository:
    """The calendar timer of the SAPS Worker: one short transaction per company (SAPS-52 BR-05)."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def try_lock(self) -> AsyncIterator[bool]:
        """One SAPS Worker process releases at a time; the lock ends with its connection, also on a crash."""
        async with self._engine.connect() as conn:
            got = bool(
                await conn.scalar(text("SELECT pg_try_advisory_lock(:k)"), {"k": HOLD_RELEASE_LOCK_KEY})
            )
            try:
                yield got
            finally:
                if got:
                    await conn.scalar(text("SELECT pg_advisory_unlock(:k)"), {"k": HOLD_RELEASE_LOCK_KEY})

    async def list_companies(self) -> list[Company]:
        async with session_factory(self._engine)() as session:  # the tenant table has no row-level security
            rows = await session.execute(
                select(Tenant.id, Tenant.name).where(Tenant.is_active).order_by(Tenant.code)
            )
            return [Company(r.id, r.name) for r in rows]

    async def snapshot(self, tenant_id: UUID) -> CalendarSnapshot:
        async with session_factory(self._engine, tenant_id)() as session:
            return await calendar_snapshot(session, tenant_id)

    async def release_oldest(self, tenant_id: UUID, limit: int, *, now: datetime) -> list[UUID]:
        async with session_factory(self._engine, tenant_id)() as session, session.begin():
            ids = list(
                (
                    await session.execute(
                        select(Invoice.id)
                        .where(Invoice.tenant_id == tenant_id, Invoice.status == InvoiceStatus.ON_HOLD)
                        .order_by(Invoice.created_at, Invoice.id)
                        .limit(limit)
                        .with_for_update(skip_locked=True)
                    )
                ).scalars()
            )
            if not ids:
                return []
            await session.execute(
                update(Invoice)
                .where(Invoice.id.in_(ids))
                .values(status=InvoiceStatus.UPLOADED, updated_by=SYSTEM_ACTOR, updated_at=func.now())
            )
            session.add_all(
                InvoiceEvent(
                    tenant_id=tenant_id,
                    invoice_id=invoice_id,
                    status_from=InvoiceStatus.ON_HOLD,
                    status_to=InvoiceStatus.UPLOADED,
                    action=RELEASE_HOLD_ACTION,
                    actor=SYSTEM_ACTOR,
                    details={"by": "calendar"},
                    occurred_at=now,
                    created_by=SYSTEM_ACTOR,
                    updated_by=SYSTEM_ACTOR,
                )
                for invoice_id in ids
            )
            return ids


class SqlInvoiceHoldRepository:
    """Process now by an Accounting Manager, in one unit of work with the invoice row locked."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_invoice(self, tenant_id: UUID, invoice_id: UUID) -> HeldInvoice | None:
        row = (
            await self._session.execute(
                select(Invoice.id, Invoice.tenant_id, Invoice.status)
                .where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
                .with_for_update()
            )
        ).first()
        return None if row is None else HeldInvoice(row.id, row.tenant_id, row.status)

    async def release_by_manager(self, invoice: HeldInvoice, *, actor: str, now: datetime) -> None:
        await self._session.execute(
            update(Invoice)
            .where(Invoice.id == invoice.id)
            .values(
                status=InvoiceStatus.UPLOADED,
                released_from_hold_at=now,
                updated_by=actor,
                updated_at=func.now(),
            )
        )
        self._session.add(
            InvoiceEvent(
                tenant_id=invoice.tenant_id,
                invoice_id=invoice.id,
                status_from=InvoiceStatus.ON_HOLD,
                status_to=InvoiceStatus.UPLOADED,
                action=RELEASE_HOLD_ACTION,
                actor=actor,
                details={"by": "manager"},
                occurred_at=now,
                created_by=actor,
                updated_by=actor,
            )
        )
        await self._session.flush()


class SqlHoldUnitOfWork:
    """One transaction per call; the end of the block commits, an error rolls back."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[SqlInvoiceHoldRepository]:
        async with self._sessions() as session, session.begin():
            yield SqlInvoiceHoldRepository(session)
