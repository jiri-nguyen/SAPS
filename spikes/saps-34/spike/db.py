"""SAPS-34 spike: async SQLAlchemy models and lazy engine (one engine per event loop)."""
import asyncio
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DB_URL = "postgresql+psycopg://saps:saps@localhost:55432/saps"


class Base(DeclarativeBase):
    pass


class Invoice(Base):
    __tablename__ = "invoice"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(30))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InvoiceEvent(Base):
    __tablename__ = "invoice_event"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    invoice_id: Mapped[uuid.UUID]
    action: Mapped[str] = mapped_column(String(50))
    actor: Mapped[str] = mapped_column(String(100))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Marker(Base):
    __tablename__ = "marker"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tag: Mapped[str] = mapped_column(String(50))
    stage: Mapped[str] = mapped_column(String(50))


_engines: dict[int, AsyncEngine] = {}


def get_engine() -> AsyncEngine:
    """Engine bound to the running event loop (async pools must not cross loops)."""
    loop_id = id(asyncio.get_running_loop())
    if loop_id not in _engines:
        _engines[loop_id] = create_async_engine(DB_URL, pool_size=5, pool_pre_ping=True)
    return _engines[loop_id]


def session_factory():
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def reset_schema():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    _engines.clear()


async def scalar(sql: str, **params):
    async with get_engine().connect() as conn:
        return await conn.scalar(text(sql), params)
