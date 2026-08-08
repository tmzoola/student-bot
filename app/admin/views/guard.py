import datetime as dt
from dataclasses import dataclass
from typing import Any

from admin.views.base import BaseAdminView
from models.base import TASHKENT_TZ
from aiogram import Bot
from core.config import settings
from starlette.requests import Request
from starlette_admin import StringField
from starlette_admin.actions import row_action
from starlette_admin.exceptions import ActionFailed


@dataclass
class GuardPhotoField(StringField):
    """Saqlangan profil rasmini detail sahifada <img> qilib ko'rsatadi."""
    display_template: str = "displays/guard_photo.html"


class JoinEventAdminView(BaseAdminView):
    name = "Qo'shilish"
    label = "Guard: barcha qo'shilishlar"
    icon = "fa fa-user-plus"

    column_list = [
        "id", "full_name", "username", "user_id",
        "chat_title", "has_photo", "nsfw_score", "flagged", "createdAt",
    ]
    column_searchable_list = ["full_name", "username", "chat_title"]
    column_sortable_list = ["nsfw_score", "flagged", "createdAt"]

    def can_create(self, request: Request) -> bool:
        return False

    def can_edit(self, request: Request) -> bool:
        return False


class FlaggedUserAdminView(BaseAdminView):
    name = "Ogohlantirish"
    label = "⚠️ Guard: ogohlantirilganlar"
    icon = "fa fa-triangle-exclamation"

    fields = [
        "id",
        GuardPhotoField("photo_path", label="Sababchi rasm", read_only=True),
        StringField("full_name", label="Ism", read_only=True),
        StringField("username", label="Username", read_only=True),
        "user_id",
        StringField("chat_title", label="Guruh", read_only=True),
        "chat_id",
        "nsfw_score",
        StringField("reasons", label="Sabab", read_only=True),
        StringField("action", label="Holat", read_only=True),
        StringField("decided_by", label="Qaror qabul qildi", read_only=True),
        "decided_at",
    ]
    column_searchable_list = ["full_name", "username", "reasons"]
    column_sortable_list = ["nsfw_score", "action", "createdAt"]

    def can_create(self, request: Request) -> bool:
        return False

    @row_action(
        name="ban_user",
        text="🚫 Guruhdan bloklash",
        confirmation="Bu foydalanuvchini guruhdan bloklaysizmi?",
        icon_class="fas fa-ban",
        submit_btn_text="Ha, bloklash",
        submit_btn_class="btn-danger",
    )
    async def ban_user_action(self, request: Request, pk: Any) -> str:
        row = await self.find_by_pk(request, pk)
        if row is None:
            raise ActionFailed("Yozuv topilmadi")
        if row.action == "banned":
            raise ActionFailed("Bu foydalanuvchi allaqachon bloklangan")

        bot = Bot(settings.GUARD_BOT_TOKEN)
        try:
            await bot.ban_chat_member(row.chat_id, row.user_id)
        except Exception as e:
            raise ActionFailed(f"Telegram xatosi: {e}") from e
        finally:
            await bot.session.close()

        session = request.state.session
        row.action = "banned"
        row.decided_by = request.session.get("username", "admin-panel")
        row.decided_at = dt.datetime.now(TASHKENT_TZ)
        await session.commit()
        return f"{row.full_name} guruhdan bloklandi 🚫"
