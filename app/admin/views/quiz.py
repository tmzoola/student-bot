from admin.views.base import BaseAdminView
from starlette_admin import BooleanField, HasOne, IntegerField, StringField, TextAreaField


class QuizAdminView(BaseAdminView):
    name = "Test"
    label = "Testlar"
    icon = "fa fa-list-check"

    fields = [
        "id",
        HasOne("topic", label="Mavzu", identity="mavzu"),
        StringField("title", label="Sarlavha", required=True),
        TextAreaField("description", label="Tavsif"),
        IntegerField("time_limit_seconds", label="Vaqt chegarasi (soniya)"),
        BooleanField("is_active", label="Faol"),
    ]

    column_list = ["id", "title", "topic", "time_limit_seconds", "is_active", "createdAt"]
    column_searchable_list = ["title"]
    column_sortable_list = ["is_active", "createdAt"]
