from admin.views.base import BaseAdminView
from starlette_admin import (
    BooleanField,
    DateTimeField,
    HasOne,
    IntegerField,
    StringField,
)


class StudentProfileAdminView(BaseAdminView):
    name = "Talaba profili"
    label = "Talaba profillari"
    icon = "fa fa-id-card"

    fields = [
        "id",
        HasOne("telegram_user", label="Telegram foydalanuvchi", identity="foydalanuvchi"),
        StringField("student_id_number", label="Talaba ID raqami", required=True),
        StringField("full_name", label="F.I.Sh", required=True),
        HasOne("faculty", label="Fakultet", identity="fakultet"),
        IntegerField("course_number", label="Kurs (1..4)", required=True),
        IntegerField("semester", label="Semestr (1..2)", required=True),
        BooleanField("is_approved", label="Tasdiqlangan"),
        DateTimeField("approved_at", label="Tasdiqlangan sanasi", read_only=True),
    ]

    column_list = [
        "id",
        "student_id_number",
        "full_name",
        "faculty",
        "course_number",
        "semester",
        "is_approved",
        "createdAt",
    ]
    column_searchable_list = ["student_id_number", "full_name"]
    column_sortable_list = ["course_number", "semester", "is_approved", "createdAt"]
