"""Test fixture'lari — bo'sh SQLite bazani `session_factory` o'rniga qo'yadi.

Postgres-spetsifik `server_default=TIMEZONE(...)` iboralari SQLite'da
qo'llab-quvvatlanmaydi — ularni test uchun `CURRENT_TIMESTAMP` ga
almashtiramiz. Bu faqat testda ishlaydi va prod schema'ni o'zgartirmaydi.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Minimal env — Settings faylni yuklashi uchun.
os.environ.setdefault("SECRET_KEY", "x")
os.environ.setdefault("BOT_TOKEN", "x")
os.environ.setdefault("ADMIN_PASSWORD", "x")
os.environ.setdefault("POSTGRES_USER", "x")
os.environ.setdefault("POSTGRES_PASSWORD", "x")
os.environ.setdefault("POSTGRES_DB", "x")

# app/ paketini import path'ga qo'shish (alembic.ini bilan bir xil).
_APP = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(_APP))

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import db.session as db_session
from models.base import Base


def _sqlite_safe_defaults() -> None:
    """Postgres TIMEZONE() default'larini SQLite uchun almashtirish."""
    from datetime import datetime, timezone
    from sqlalchemy import ColumnDefault
    for table in Base.metadata.tables.values():
        for col in table.columns:
            sd = col.server_default
            if sd is None:
                continue
            raw = getattr(sd, "arg", None)
            if raw is not None and "TIMEZONE" in str(raw).upper():
                col.server_default = None
                if col.default is None:
                    default = ColumnDefault(lambda: datetime.now(timezone.utc))
                    default.column = col
                    col.default = default


@pytest_asyncio.fixture
async def async_engine():
    _sqlite_safe_defaults()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(async_engine, monkeypatch):
    factory = async_sessionmaker(async_engine, expire_on_commit=False)
    monkeypatch.setattr(db_session, "session_factory", factory)
    return factory


@pytest_asyncio.fixture
async def db(session_factory):
    async with session_factory() as session:
        yield session
