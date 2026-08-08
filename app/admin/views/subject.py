from admin.views.base import BaseAdminView
from starlette_admin import (
    BooleanField,
    HasOne,
    IntegerField,
    StringField,
    TextAreaField,
)


class SubjectAdminView(BaseAdminView):
    name = "Fan"
    label = "Fanlar"
    icon = "fa fa-book-atlas"

    fields = [
        "id",
        HasOne("faculty", label="Fakultet", identity="fakultet"),
        StringField("name", label="Nomi", required=True),
        StringField("code", label="Kod", required=True),
        IntegerField("course_number", label="Kurs (1..4)", required=True),
        IntegerField("semester", label="Semestr (1..2)", required=True),
        TextAreaField("description", label="Tavsif"),
        BooleanField("is_active", label="Faol"),
    ]

    column_list = [
        "id",
        "name",
        "faculty",
        "course_number",
        "semester",
        "is_active",
        "createdAt",
    ]
    column_searchable_list = ["name", "code"]
    column_sortable_list = ["course_number", "semester", "is_active", "createdAt"]
