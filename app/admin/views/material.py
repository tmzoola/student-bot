from admin.views.base import BaseAdminView
from models.material import MaterialStatus
from starlette_admin import (
    EnumField,
    HasOne,
    IntegerField,
    StringField,
    TextAreaField,
)


class MaterialAdminView(BaseAdminView):
    name = "Material"
    label = "Materiallar"
    icon = "fa fa-file-lines"

    fields = [
        "id",
        HasOne("student_profile", label="Talaba", identity="talaba-profili"),
        StringField("title", label="Sarlavha", required=True),
        StringField("filename", label="Fayl nomi"),
        StringField("mime", label="MIME"),
        IntegerField("size_bytes", label="Hajm (bayt)"),
        StringField("storage_path", label="Saqlash yo'li"),
        EnumField("status", label="Holat", enum=MaterialStatus),
        IntegerField("extracted_text_length", label="Matn uzunligi"),
        TextAreaField("error_message", label="Xato sababi"),
    ]

    column_list = [
        "id",
        "title",
        "student_profile",
        "size_bytes",
        "status",
        "extracted_text_length",
        "createdAt",
    ]
    column_searchable_list = ["title", "filename"]
    column_sortable_list = ["status", "size_bytes", "createdAt"]
