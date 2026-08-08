"""Bot asosiy menyusi (reply keyboard) sozlamalari — singleton.

Admin paneldan 4ta pastki tugmani (Test ishlash / Kitoblar do'koni / Ma'lumot /
Taklif linki) yoqib/o'chirish uchun. Bitta qator seed qilinadi.
"""
from models.base import Base
from sqlalchemy import Boolean
from sqlalchemy.orm import Mapped, mapped_column


class MenuSettings(Base):
    __tablename__ = "menu_settings"

    show_test: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    show_books: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    show_info: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    show_referral: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )

    def __str__(self) -> str:
        return "Menyu sozlamalari"
