import enum
from typing import TYPE_CHECKING

from models.base import Base
from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from models.telegram_user import TelegramUser


class OrderStatus(str, enum.Enum):
    PENDING = "pending"              # Order created, awaiting payment
    CONFIRMED = "confirmed"          # Admin confirmed payment; asking user for address
    PROCESSING = "processing"        # Delivery info received; preparing to ship
    SHIPPED = "shipped"              # Book dispatched


class ShopSettings(Base):
    """Singleton row: card details & admin Telegram ID for the book shop."""
    __tablename__ = "shop_settings"

    card_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    card_holder: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Telegram ID of the admin who receives payment screenshots
    admin_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    admin_username: Mapped[str | None] = mapped_column(String(128), nullable=True)

    def __str__(self) -> str:
        return f"Do'kon sozlamalari (#{self.id})"


class ShopBook(Base):
    __tablename__ = "shop_books"

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[int] = mapped_column(Integer, default=0)   # UZS
    cover_image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    order: Mapped[int] = mapped_column(Integer, default=0)

    def __str__(self) -> str:
        return self.title


class BookOrder(Base):
    __tablename__ = "book_orders"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_users.id", ondelete="CASCADE"), index=True
    )
    book_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shop_books.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            name="order_status_enum",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=OrderStatus.PENDING,
    )
    delivery_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    delivery_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["TelegramUser"] = relationship("TelegramUser", lazy="select")
    book: Mapped["ShopBook"] = relationship("ShopBook", lazy="select")

    def __str__(self) -> str:
        return f"Buyurtma #{self.id}"
