from admin.views.base import BaseAdminView
from starlette_admin import BooleanField, StringField


class FacultyAdminView(BaseAdminView):
    name = "Fakultet"
    label = "Fakultetlar"
    icon = "fa fa-building-columns"

    fields = [
        "id",
        StringField("name", label="Nomi", required=True),
        StringField("code", label="Kod (unique)", required=True),
        BooleanField("is_active", label="Faol"),
    ]

    column_list = ["id", "name", "code", "is_active", "createdAt"]
    column_searchable_list = ["name", "code"]
    column_sortable_list = ["name", "is_active", "createdAt"]
