from sqlalchemy.ext.asyncio import async_sessionmaker

from saps.adapters.persistence import db


async def test_one_engine_per_event_loop_and_dispose() -> None:
    url = "postgresql+psycopg://u:p@127.0.0.1:1/x"
    first = db.get_engine(url)
    assert db.get_engine(url) is first
    assert isinstance(db.session_factory(first), async_sessionmaker)
    await db.dispose_engines()
    assert db.get_engine(url) is not first
    await db.dispose_engines()


async def test_unreachable_database_is_reported_without_raising() -> None:
    engine = db.get_engine("postgresql+psycopg://u:p@127.0.0.1:1/x")
    assert await db.database_is_reachable(engine) is False
    await db.dispose_engines()
