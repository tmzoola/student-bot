from admin.views.base import BaseAdminView
from starlette_admin import BooleanField, IntegerField, StringField
from starlette.requests import Request


class TelegramUserAdminView(BaseAdminView):
    name = "Foydalanuvchi"
    label = "Foydalanuvchilar"
    icon = "fa fa-users"

    fields = [
        "id",
        IntegerField("telegram_id", label="Telegram ID", read_only=True),
        StringField("username", label="Username", read_only=True),
        StringField("first_name", label="Ism", read_only=True),
        StringField("last_name", label="Familiya", read_only=True),
        StringField("language_code", label="Til", read_only=True),
        StringField("phone", label="Telefon", read_only=True),
        BooleanField("is_banned", label="Qora ro'yxat (bloklash)"),
        BooleanField("is_blocked", label="Botni bloklagan", read_only=True),
    ]

    column_list = ["id", "telegram_id", "username", "first_name", "phone", "is_banned", "is_blocked", "createdAt"]
    column_searchable_list = ["username", "first_name", "last_name", "phone"]
    column_sortable_list = ["is_banned", "is_blocked", "createdAt"]

    def can_create(self, request: Request) -> bool:
        return False

    def can_delete(self, request: Request) -> bool:
        return True
