from admin.views.base import BaseAdminView
from starlette_admin import BooleanField, DateTimeField, IntegerField, StringField, TextAreaField


class DeadlineAdminView(BaseAdminView):
    name = "Deadline"
    label = "Deadlinelar"
    icon = "fa fa-calendar-check"

    fields = [
        "id",
        StringField("title", label="Sarlavha", required=True),
        TextAreaField("description", label="Tavsif"),
        DateTimeField("deadline_at", label="Muddat", required=True),
        IntegerField("faculty_id", label="Fakultet ID (bo'sh = hammaga)"),
        BooleanField("is_active", label="Faol"),
        IntegerField("created_by", label="Yaratuvchi (Telegram ID)"),
    ]

    column_list = ["id", "title", "deadline_at", "faculty_id", "is_active", "createdAt"]
    column_searchable_list = ["title"]
    column_sortable_list = ["deadline_at", "is_active", "createdAt"]
