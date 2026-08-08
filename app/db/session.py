from collections.abc import AsyncGenerator
from typing import Callable

from core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# create an async engine
# Pool sozlamalari 1000+ parallel foydalanuvchi uchun. Postgres tarafida
# `max_connections` bunga mos bo'lishi kerak (default 100 dan 200+ ga oshirish
# tavsiya etiladi — docker-compose.yml da `command`ga qo'shing).
engine = create_async_engine(
    url=settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,          # doimiy ochiq ulanishlar
    max_overflow=40,       # cho'qqi yuklamada qo'shimcha (jami 60 gacha)
    pool_pre_ping=True,    # zombi ulanishlarni oldindan tekshirish
    pool_recycle=1800,     # 30 daqiqada qayta ochish (Postgres idle timeout)
    pool_timeout=10,       # navbatda kutish (aks holda default 30s)
    connect_args={"server_settings": {"timezone": "Asia/Tashkent"}},
)
# expire_on_commit=False so ORM attributes stay usable after commit without
# triggering sync lazy-loads on the async session.
session_factory: Callable[[], AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency for getting database session
    """
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
