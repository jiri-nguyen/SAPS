"""SQLAlchemy async engine and sessions (ADR-0005)."""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base of all ORM models; Alembic reads its metadata."""


_engines: dict[int, AsyncEngine] = {}


def get_engine(database_url: str) -> AsyncEngine:
    """One engine per event loop: async pools must not cross loops (ADR-0004 spike finding)."""
    key = id(asyncio.get_running_loop())
    engine = _engines.get(key)
    if engine is None:
        engine = create_async_engine(database_url, pool_pre_ping=True)
        _engines[key] = engine
    return engine


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


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
