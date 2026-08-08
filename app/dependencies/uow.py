from typing import Annotated, AsyncGenerator

from db.session import session_factory
from fastapi import Depends
from uow.impl import UnitOfWork
from uow.ports import UnitOfWorkABC

# def get_unit_of_work() -> UnitOfWorkABC:
#     return UnitOfWork(session_factory)


async def get_unit_of_work() -> AsyncGenerator[UnitOfWorkABC, None]:
    """
    Dependency that provides a properly managed UnitOfWork (UoW) instance per request.

    ⚠️ Why this is important:
        In the previous implementation, we simply returned `UnitOfWork(session_factory)`
        without entering its async context (i.e., without calling `__aenter__`).
        This meant that:
            - The database session was never actually opened
            - Repository attributes like `user_hotel_type` were never initialized
            - Connections could leak or remain unclosed

    ✅ This fixed implementation uses `async with`:
        - Ensures `UnitOfWork.__aenter__()` is called automatically
        - Initializes all repositories (user_hotel_type, user, org, etc.)
        - Opens a database session tied to the request lifecycle
        - Cleans up resources safely by calling `__aexit__()` at the end of the request,
          committing or rolling back as needed.

    Usage:
        This dependency can be injected into any FastAPI route or service:
            async def endpoint(uow: Annotated[UnitOfWorkABC, Depends(get_unit_of_work)]):
                ...

    Returns:
        An active UnitOfWork instance ready for use within the request scope.
    """
    async with UnitOfWork(session_factory) as uow:
        yield uow


UowDependency = Annotated[UnitOfWorkABC, Depends(get_unit_of_work)]
