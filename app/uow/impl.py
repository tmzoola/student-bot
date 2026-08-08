from collections.abc import Callable
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession
from uow.ports import UnitOfWorkABC


class UnitOfWork(UnitOfWorkABC):
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        if self._session is None:
            return

        if exc_type:
            await self.rollback()
        else:
            await self.commit()

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("Session not initialized. Use as context manager.")

        try:
            await self._session.commit()
        except Exception:
            await self.rollback()
            raise
        finally:
            await self._session.close()
            self._session = None

    async def rollback(self) -> None:
        if self._session is None:
            return

        try:
            await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None
