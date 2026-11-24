"""SQLAlchemy async engine and sessions (ADR-0005)."""

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import Connection, event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, SessionTransaction


class Base(DeclarativeBase):
    """Declarative base of all ORM models; Alembic reads its metadata."""


_engines: dict[tuple[int, str], AsyncEngine] = {}


def get_engine(database_url: str) -> AsyncEngine:
    """One engine per event loop and URL: async pools must not cross loops (ADR-0004 spike finding), and each
    database role has its own pool (SAPS-41)."""
    key = (id(asyncio.get_running_loop()), database_url)
    engine = _engines.get(key)
    if engine is None:
        engine = create_async_engine(database_url, pool_pre_ping=True)
        _engines[key] = engine
    return engine


TENANT_KEY = "tenant_id"
_SET_TENANT = text("SELECT set_config('app.tenant_id', :tenant_id, true)")


def session_factory(engine: AsyncEngine, tenant_id: UUID | None = None) -> async_sessionmaker[AsyncSession]:
    """Sessions for one company (SAPS-41).

    Every transaction starts by setting `app.tenant_id`, so row-level security limits it to that company.
    Without a company the sessions see no tenant-owned rows (fail closed).
    """
    info: dict[str, Any] = {} if tenant_id is None else {TENANT_KEY: tenant_id}
    return async_sessionmaker(engine, expire_on_commit=False, info=info)


async def set_tenant(session: AsyncSession, tenant_id: UUID) -> None:
    """Set the company on the session's current transaction (used once the company becomes known in it)."""
    session.info[TENANT_KEY] = tenant_id
    await session.execute(_SET_TENANT, {"tenant_id": str(tenant_id)})


@event.listens_for(Session, "after_begin")
def _set_tenant_on_begin(session: Session, transaction: SessionTransaction, connection: Connection) -> None:
    tenant_id = session.info.get(TENANT_KEY)
    if tenant_id is not None:
        connection.execute(_SET_TENANT, {"tenant_id": str(tenant_id)})


async def database_is_reachable(engine: AsyncEngine) -> bool:
    """Used by readiness checks; never raises."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        return False
    return True


async def dispose_engines() -> None:
    for engine in list(_engines.values()):
        await engine.dispose()
    _engines.clear()
