from starlette.requests import Request
from starlette_admin import BooleanField, HasOne, IntegerField, StringField, TextAreaField

from admin.views.base import BaseAdminView


class ShopSettingsView(BaseAdminView):
    name = "Do'kon sozlamasi"
    label = "Do'kon sozlamalari"
    icon = "fa fa-credit-card"

    fields = [
        "id",
        StringField("card_number", label="Karta raqami (masalan: 8600 1234 5678 9012)"),
        StringField("card_holder", label="Karta egasi ismi"),
        IntegerField("admin_telegram_id", label="Admin Telegram ID (screenshot qabul qiluvchi)"),
        StringField("admin_username", label="Admin username (@ siz, masalan: admin_uz)"),
    ]

    column_list = ["id", "card_number", "card_holder", "admin_username"]

    def can_create(self, request: Request) -> bool:
        return False  # singleton — only one row, seeded by migration

    def can_delete(self, request: Request) -> bool:
        return False


class ShopBookView(BaseAdminView):
    name = "Do'kon kitobi"
    label = "Do'kon kitoblari"
    icon = "fa fa-book-open"

    fields = [
        "id",
        StringField("title", label="Nomi", required=True),
        TextAreaField("description", label="Tavsif"),
        IntegerField("price", label="Narxi (so'm)", required=True),
        StringField("cover_image_url", label="Muqova rasmi URL (ixtiyoriy)"),
        IntegerField("order", label="Tartib"),
        BooleanField("is_active", label="Faol"),
    ]

    column_list = ["id", "title", "price", "is_active", "order"]
    column_sortable_list = ["order", "price", "is_active"]


class BookOrderView(BaseAdminView):
    name = "Buyurtma"
    label = "Buyurtmalar"
    icon = "fa fa-box"

    fields = [
        "id",
        HasOne("user", label="Foydalanuvchi", identity="foydalanuvchi"),
        HasOne("book", label="Kitob", identity="dokon-kitob"),
        StringField("status", label="Holat", read_only=True),
        StringField("delivery_name", label="Ism Familya", read_only=True),
        StringField("delivery_phone", label="Telefon", read_only=True),
        TextAreaField("delivery_address", label="Manzil", read_only=True),
        TextAreaField("admin_note", label="Admin eslatmasi"),
        "createdAt",
    ]

    column_list = ["id", "user", "book", "status", "delivery_name", "delivery_phone", "createdAt"]
    column_sortable_list = ["status", "createdAt"]
    column_searchable_list = ["delivery_name", "delivery_phone"]

    def can_create(self, request: Request) -> bool:
        return False
