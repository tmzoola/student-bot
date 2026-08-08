from starlette.requests import Request
from starlette_admin.contrib.sqla import ModelView


class BaseAdminView(ModelView):
    exclude_fields_from_create = ["createdAt", "updatedAt"]
    exclude_fields_from_edit = ["createdAt", "updatedAt"]
    exclude_fields_from_list = ["createdAt", "updatedAt"]

    # Default: barcha modellarda o'chirish yoqilgan. Singleton view'lar
    # (Landing, Menu, ShopSettings) alohida `can_delete → False` bilan
    # o'chirishni bloklaydi.
    def can_delete(self, request: Request) -> bool:
        return True
