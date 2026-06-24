import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def wait_for_db():
    """Подождать пока PostgreSQL будет готов."""
    for i in range(5):
        try:
            async with engine.begin() as conn:
                await conn.exec_driver_sql("SELECT 1")
            return
        except Exception:
            if i < 4:
                await asyncio.sleep(2)
            else:
                raise


async def get_db():
    async with async_session() as session:
        yield session
