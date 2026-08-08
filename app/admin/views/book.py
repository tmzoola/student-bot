import uuid
from pathlib import Path
from typing import Any

from admin.views.base import BaseAdminView
from core.config import ALLOWED_BOOK_EXT, BOOKS_DIR_NAME, MAX_BOOK_SIZE, MEDIA_ROOT
from starlette.requests import Request
from starlette_admin import (
    BooleanField,
    FileField,
    HasOne,
    IntegerField,
    RequestAction,
    StringField,
    TextAreaField,
)
from starlette_admin.exceptions import FormValidationError


class BookAdminView(BaseAdminView):
    name = "Kitob"
    label = "Kitoblar"
    icon = "fa fa-book-open"

    fields = [
        "id",
        StringField("title", label="Sarlavha", required=True),
        StringField("author", label="Muallif"),
        StringField("category", label="Turi"),
        HasOne("topic", label="Mavzu", identity="mavzu"),
        TextAreaField("description", label="Tavsif"),
        FileField(
            "upload",
            label="Fayl",
            help_text="PDF, DOC(X), PPT(X), XLS(X), EPUB, DJVU, TXT · maks. 100 MB",
            exclude_from_list=True,
            exclude_from_detail=True,
        ),
        StringField("file_name", label="Joriy fayl", read_only=True,
                    exclude_from_create=True),
        IntegerField("file_size", label="Hajmi (bayt)", read_only=True,
                     exclude_from_create=True),
        IntegerField("downloads", label="Yuklab olishlar", read_only=True,
                     exclude_from_create=True),
        IntegerField("order", label="Tartib"),
        BooleanField("is_active", label="Faol"),
    ]

    exclude_fields_from_list = BaseAdminView.exclude_fields_from_list + ["file_path", "description"]

    column_list = ["id", "title", "category", "topic", "file_name", "downloads", "is_active"]
    column_searchable_list = ["title", "author", "category"]
    column_sortable_list = ["is_active", "downloads", "createdAt"]

    # ── file handling ──────────────────────────────────────────────

    async def _store_upload(self, obj: Any, upload: Any) -> None:
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in ALLOWED_BOOK_EXT:
            raise FormValidationError({"upload": f"Fayl turi qo'llab-quvvatlanmaydi: {ext or 'nomaʼlum'}"})
        data = await upload.read()
        if not data:
            raise FormValidationError({"upload": "Fayl bo'sh"})
        if len(data) > MAX_BOOK_SIZE:
            raise FormValidationError({"upload": "Fayl juda katta (maks. 100 MB)"})

        books_dir = MEDIA_ROOT / BOOKS_DIR_NAME
        books_dir.mkdir(parents=True, exist_ok=True)
        stored = f"{BOOKS_DIR_NAME}/{uuid.uuid4().hex}{ext}"
        (MEDIA_ROOT / stored).write_bytes(data)

        old = getattr(obj, "file_path", None)
        obj.file_path = stored
        obj.file_name = upload.filename or f"kitob{ext}"
        obj.file_size = len(data)
        if old and old != stored:
            try:
                (MEDIA_ROOT / old).unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _extract_upload(data: dict) -> Any:
        raw = data.get("upload")
        upload = raw[0] if isinstance(raw, tuple) else raw
        if upload is not None and getattr(upload, "filename", ""):
            return upload
        return None

    async def validate(self, request: Request, data: dict) -> None:
        # A file is mandatory when creating a new book (file_path is NOT NULL).
        if request.state.action == RequestAction.CREATE and self._extract_upload(data) is None:
            raise FormValidationError({"upload": "Fayl majburiy"})
        await super().validate(request, data)

    async def _populate_obj(self, request: Request, obj: Any, data: dict, is_edit: bool = False) -> Any:
        obj = await super()._populate_obj(request, obj, data, is_edit)
        upload = self._extract_upload(data)
        if upload is not None:
            await self._store_upload(obj, upload)
        # `upload` is a virtual field — drop the raw UploadFile super() set on obj
        if hasattr(obj, "upload"):
            try:
                delattr(obj, "upload")
            except AttributeError:
                pass
        return obj

    async def delete(self, request: Request, pks: list) -> int | None:
        # Remove files from disk alongside the DB rows
        for pk in pks:
            obj = await self.find_by_pk(request, pk)
            if obj and obj.file_path:
                try:
                    (MEDIA_ROOT / obj.file_path).unlink(missing_ok=True)
                except OSError:
                    pass
        return await super().delete(request, pks)
