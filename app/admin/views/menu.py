"""Bot asosiy menyu (reply keyboard) sozlamalari admin view — singleton."""
from starlette.requests import Request
from starlette_admin import BooleanField

from admin.views.base import BaseAdminView


class MenuSettingsView(BaseAdminView):
    name = "Menyu sozlamasi"
    label = "Bot menyu tugmalari"
    icon = "fa fa-list"

    fields = [
        "id",
        BooleanField("show_test", label="🎓 Test ishlash tugmasi"),
        BooleanField("show_books", label="📚 Kitoblar do'koni tugmasi"),
        BooleanField("show_info", label="ℹ️ Ma'lumot tugmasi"),
        BooleanField("show_referral", label="🔗 Taklif linki tugmasi"),
        "updatedAt",
    ]

    column_list = ["id", "show_test", "show_books", "show_info", "show_referral"]

    def can_create(self, request: Request) -> bool:
        return False  # singleton — migratsiyada seed qilinadi

    def can_delete(self, request: Request) -> bool:
        return False
