from admin.views.base import BaseAdminView
from starlette.requests import Request
from starlette_admin import StringField, TextAreaField


class LandingContentAdminView(BaseAdminView):
    name = "Bosh sahifa matni"
    label = "Bosh sahifa matni"
    icon = "fa fa-pen-to-square"

    fields = [
        "id",
        StringField("badge_text", label="Yuqoridagi belgi (badge)", required=True),
        StringField("hero_title_before", label="Sarlavha (boshi)", required=True),
        StringField("hero_title_highlight", label="Sarlavha (yashil so'z)", required=True),
        StringField("hero_title_after", label="Sarlavha (oxiri)", required=True),
        TextAreaField("hero_subtitle", label="Tavsif", required=True),
        StringField("primary_btn_label", label="Asosiy tugma", required=True),
        StringField("secondary_btn_label", label="Ikkinchi tugma", required=True),
        StringField("daily_title", label="Kunlik test sarlavhasi", required=True),
    ]

    column_list = ["id", "badge_text", "primary_btn_label", "updatedAt"]

    def can_create(self, request: Request) -> bool:
        return False

    def can_delete(self, request: Request) -> bool:
        return False
