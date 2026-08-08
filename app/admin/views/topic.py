from admin.views.base import BaseAdminView
from starlette_admin import BooleanField, HasOne, IntegerField, StringField, TextAreaField


class TopicAdminView(BaseAdminView):
    name = "Mavzu"
    label = "Mavzular"
    icon = "fa fa-book"

    fields = [
        "id",
        HasOne("subject", label="Fan", identity="fan"),
        StringField("title", label="Sarlavha", required=True),
        TextAreaField("description", label="Tavsif"),
        IntegerField("order", label="Tartib"),
        BooleanField("is_active", label="Faol"),
    ]

    column_list = ["id", "title", "subject", "order", "is_active", "createdAt"]
    column_searchable_list = ["title"]
    column_sortable_list = ["order", "is_active", "createdAt"]
