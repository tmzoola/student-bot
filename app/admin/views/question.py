import uuid
from pathlib import Path
from typing import Any

from admin.views.base import BaseAdminView
from core.config import (
    ALLOWED_IMAGE_EXT,
    MAX_IMAGE_SIZE,
    MEDIA_ROOT,
    QUESTION_IMAGES_DIR_NAME,
)
from models.question import CorrectOption
from starlette.requests import Request
from starlette_admin import (
    EnumField,
    FileField,
    HasOne,
    IntegerField,
    StringField,
    TextAreaField,
)
from starlette_admin.exceptions import FormValidationError


class QuestionAdminView(BaseAdminView):
    name = "Savol"
    label = "Savollar"
    icon = "fa fa-question-circle"

    fields = [
        "id",
        HasOne("quiz", label="Test", identity="test"),
        IntegerField("order", label="Tartib"),
        TextAreaField("text", label="Savol matni (rasm bo'lsa ixtiyoriy)", required=False),
        FileField(
            "image_upload",
            label="Rasm yuklash (ixtiyoriy)",
            help_text="PNG, JPG, JPEG, WEBP, GIF · maks. 5 MB. Yuklansa mavjud rasm almashadi.",
            exclude_from_list=True,
        ),
        StringField(
            "image_url",
            label="Joriy rasm (URL). Tozalash uchun bo'shating.",
        ),
        StringField("option_a", label="A variant", required=True),
        StringField("option_b", label="B variant", required=True),
        StringField("option_c", label="C variant", required=True),
        StringField("option_d", label="D variant", required=True),
        EnumField("correct_option", label="To'g'ri javob", enum=CorrectOption, required=True),
        TextAreaField("explanation", label="Izoh (ixtiyoriy)"),
    ]

    column_list = ["id", "quiz", "order", "text", "correct_option"]
    column_searchable_list = ["text"]
    column_sortable_list = ["order"]
    page_size = 50

    # ── rasm yuklash (book.py pattern) ──────────────────────────────

    async def _store_image(self, obj: Any, upload: Any) -> None:
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in ALLOWED_IMAGE_EXT:
            raise FormValidationError(
                {"image_upload": f"Rasm turi qo'llab-quvvatlanmaydi: {ext or 'nomaʼlum'}"}
            )
        data = await upload.read()
        if not data:
            raise FormValidationError({"image_upload": "Fayl bo'sh"})
        if len(data) > MAX_IMAGE_SIZE:
            raise FormValidationError({"image_upload": "Rasm juda katta (maks. 5 MB)"})

        images_dir = MEDIA_ROOT / QUESTION_IMAGES_DIR_NAME
        images_dir.mkdir(parents=True, exist_ok=True)
        stored = f"{QUESTION_IMAGES_DIR_NAME}/{uuid.uuid4().hex}{ext}"
        (MEDIA_ROOT / stored).write_bytes(data)

        old = getattr(obj, "image_url", None)
        obj.image_url = f"/media/{stored}"
        # Eski yuklangan faylni (media ichidagini) tozalaymiz.
        if old and old.startswith("/media/"):
            try:
                (MEDIA_ROOT / old[len("/media/"):]).unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _extract_upload(data: dict) -> Any:
        raw = data.get("image_upload")
        upload = raw[0] if isinstance(raw, tuple) else raw
        if upload is not None and getattr(upload, "filename", ""):
            return upload
        return None

    async def _populate_obj(
        self, request: Request, obj: Any, data: dict, is_edit: bool = False
    ) -> Any:
        obj = await super()._populate_obj(request, obj, data, is_edit)
        upload = self._extract_upload(data)
        if upload is not None:
            await self._store_image(obj, upload)
        # `image_upload` — virtual maydon; xom UploadFile'ni obj'dan olib tashlaymiz.
        if hasattr(obj, "image_upload"):
            try:
                delattr(obj, "image_upload")
            except AttributeError:
                pass
        return obj
