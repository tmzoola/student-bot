from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import TIMESTAMP, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")


class Base(DeclarativeBase):
    """
    Base class for all models.
    This class is used to define the base for all SQLAlchemy models.
    It inherits from DeclarativeBase, which is a base class for declarative models.
    """

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    createdAt: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("TIMEZONE('Asia/Tashkent', now())"),
        name="created_at",
    )
    updatedAt: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("TIMEZONE('Asia/Tashkent', now())"),
        onupdate=lambda: datetime.now(TASHKENT_TZ),
        name="updated_at",
    )
    deletedAt: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        name="deleted_at",
        index=True,
    )
