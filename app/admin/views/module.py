from admin.views.base import BaseAdminView
from starlette_admin import BooleanField, IntegerField, StringField, TextAreaField


class ModuleAdminView(BaseAdminView):
    name = "Modul"
    label = "Modullar"
    icon = "fa fa-layer-group"

    fields = [
        "id",
        StringField("title", label="Sarlavha", required=True),
        TextAreaField("description", label="Tavsif"),
        StringField("icon", label="Ikonka (FA class, masalan: fa fa-atom)"),
        StringField("color", label="Rang (hex, masalan: #6c8cff)"),
        IntegerField("order", label="Tartib"),
        BooleanField("is_active", label="Faol"),
    ]

    column_list = ["id", "title", "order", "is_active", "createdAt"]
    column_searchable_list = ["title"]
    column_sortable_list = ["order", "is_active", "createdAt"]
