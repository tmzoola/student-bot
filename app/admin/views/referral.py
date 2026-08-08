"""Referral (taklif) tizimi uchun admin panel view'lari.

Modellar: TrackedChat, InviteLink, InviteJoin (`app/models/referral.py`).

Barcha view'lar ko'p jihatdan **read-only** — invite linklar va qo'shilish
hodisalari faqat Telegram / bot service tomonidan yaratiladi. TrackedChat
uchun faqat `is_active` toggle qilinishi mumkin.
"""
import uuid
from pathlib import Path
from typing import Any

from admin.views.base import BaseAdminView
from core.config import ALLOWED_IMAGE_EXT, MAX_IMAGE_SIZE, MEDIA_ROOT
from starlette.requests import Request
from starlette_admin import (
    BooleanField,
    DateTimeField,
    FileField,
    HasOne,
    IntegerField,
    StringField,
    TextAreaField,
)
from starlette_admin.exceptions import FormValidationError

# Konkurs e'lon rasmlari MEDIA_ROOT ichida shu papkaga saqlanadi.
REFERRAL_EVENTS_DIR_NAME = "referral_events"


class TrackedChatAdminView(BaseAdminView):
    name = "Kuzatiladigan chat"
    label = "Referral: kuzatiladigan chats"
    icon = "fa fa-hashtag"

    fields = [
        "id",
        IntegerField("chat_id", label="Telegram chat ID", read_only=True),
        StringField("title", label="Nomi", read_only=True),
        StringField("type", label="Turi", read_only=True),
        StringField("username", label="Username", read_only=True),
        StringField(
            "invite_url",
            label="Qo'shilish havolasi (private uchun)",
            required=False,
            help_text="Private kanal/guruh uchun doimiy invite link. "
            "Public bo'lsa username'dan avtomatik olinadi.",
        ),
        BooleanField("is_active", label="Faol"),
        "createdAt",
        "updatedAt",
    ]

    column_list = [
        "id",
        "chat_id",
        "title",
        "type",
        "username",
        "invite_url",
        "is_active",
        "createdAt",
        "updatedAt",
    ]
    column_searchable_list = ["title", "username", "chat_id"]
    column_sortable_list = ["createdAt", "is_active", "type"]
    fields_default_sort = [("createdAt", True)]

    def can_create(self, request: Request) -> bool:
        return False


class InviteLinkAdminView(BaseAdminView):
    name = "Taklif linki"
    label = "Referral: taklif linklari"
    icon = "fa fa-link"

    fields = [
        "id",
        HasOne("user", label="Foydalanuvchi", identity="foydalanuvchi"),
        HasOne("tracked_chat", label="Chat", identity="referral-tracked-chat"),
        StringField("invite_link", label="Invite link", read_only=True),
        StringField("telegram_link_name", label="Telegram link nomi", read_only=True),
        IntegerField("join_count", label="Qo'shilganlar soni", read_only=True),
        "createdAt",
        StringField("revoked_at", label="Bekor qilingan sana", read_only=True),
    ]

    column_list = [
        "id",
        "user",
        "tracked_chat",
        "invite_link",
        "telegram_link_name",
        "join_count",
        "createdAt",
        "revoked_at",
    ]
    column_searchable_list = ["telegram_link_name", "invite_link"]
    column_sortable_list = ["join_count", "createdAt", "revoked_at"]
    fields_default_sort = [("join_count", True)]

    def can_create(self, request: Request) -> bool:
        return False

    def can_edit(self, request: Request) -> bool:
        return False


class RewardTierAdminView(BaseAdminView):
    """T-021 · Reward tier CRUD — admin bosqichlarni sozlaydi."""

    name = "Sovg'a bosqichi"
    label = "Referral: sovg'a bosqichlari"
    icon = "fa fa-gift"

    fields = [
        "id",
        StringField("title", label="Nomi", required=True),
        TextAreaField("description", label="Tavsif", required=False),
        IntegerField(
            "required_invites",
            label="Kerakli takliflar soni",
            required=True,
        ),
        BooleanField("is_active", label="Faol"),
        StringField("image_url", label="Rasm URL (ixtiyoriy)", required=False),
        "createdAt",
        "updatedAt",
    ]

    column_list = [
        "id",
        "title",
        "required_invites",
        "is_active",
        "createdAt",
    ]
    column_searchable_list = ["title"]
    column_sortable_list = ["required_invites", "is_active", "createdAt"]
    fields_default_sort = [("required_invites", False)]


class UserRewardAdminView(BaseAdminView):
    """T-021 · User reward — read-only + `claimed_at`/`note` tahrirlash."""

    name = "Qozonilgan sovg'a"
    label = "Referral: qozonilgan sovg'alar"
    icon = "fa fa-trophy"

    fields = [
        "id",
        HasOne("user", label="Foydalanuvchi", identity="foydalanuvchi"),
        HasOne(
            "reward_tier",
            label="Sovg'a bosqichi",
            identity="referral-reward-tier",
        ),
        DateTimeField("earned_at", label="Qozonilgan sana", read_only=True),
        DateTimeField(
            "claimed_at",
            label="Yetkazilgan sana",
            required=False,
        ),
        TextAreaField("note", label="Admin izohi", required=False),
        "createdAt",
    ]

    column_list = [
        "id",
        "user",
        "reward_tier",
        "earned_at",
        "claimed_at",
        "note",
    ]
    column_sortable_list = ["earned_at", "claimed_at"]
    fields_default_sort = [("earned_at", True)]

    def can_create(self, request: Request) -> bool:
        return False


class ReferralEventAdminView(BaseAdminView):
    """Referral konkurs (event) CRUD — admin e'lonni sozlaydi."""

    name = "Referral konkurs"
    label = "Referral: konkurslar"
    icon = "fa fa-bullhorn"

    fields = [
        "id",
        StringField("title", label="Sarlavha", required=True),
        TextAreaField(
            "announcement_text",
            label="E'lon matni (/start'da ko'rsatiladi)",
            required=True,
        ),
        TextAreaField(
            "share_text",
            label="Ulashish matni (do'stlarga ulashishda). Bo'sh bo'lsa e'lon matni ishlatiladi",
            required=False,
        ),
        FileField(
            "image_upload",
            label="E'lon rasmi (ixtiyoriy)",
            help_text="PNG, JPG, JPEG, WEBP, GIF · maks. 5 MB",
            exclude_from_list=True,
            exclude_from_detail=True,
        ),
        StringField(
            "image_url",
            label="Joriy rasm",
            read_only=True,
            exclude_from_create=True,
        ),
        TextAreaField(
            "success_text",
            label="Chipta xabari sarlavhasi (ixtiyoriy)",
            required=False,
        ),
        DateTimeField("starts_at", label="Boshlanish vaqti", required=True),
        DateTimeField("ends_at", label="Tugash vaqti", required=True),
        BooleanField("is_active", label="Faol"),
        "createdAt",
        "updatedAt",
    ]

    column_list = [
        "id",
        "title",
        "starts_at",
        "ends_at",
        "is_active",
        "createdAt",
    ]
    column_searchable_list = ["title"]
    column_sortable_list = ["starts_at", "ends_at", "is_active", "createdAt"]
    fields_default_sort = [("starts_at", True)]

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

        images_dir = MEDIA_ROOT / REFERRAL_EVENTS_DIR_NAME
        images_dir.mkdir(parents=True, exist_ok=True)
        stored = f"{REFERRAL_EVENTS_DIR_NAME}/{uuid.uuid4().hex}{ext}"
        (MEDIA_ROOT / stored).write_bytes(data)

        old = getattr(obj, "image_url", None)
        obj.image_url = stored
        if old and old != stored and not old.startswith(("http://", "https://")):
            try:
                (MEDIA_ROOT / old).unlink(missing_ok=True)
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
        # `image_upload` — virtual maydon; super() qo'ygan xom UploadFile'ni olib tashlaymiz.
        if hasattr(obj, "image_upload"):
            try:
                delattr(obj, "image_upload")
            except AttributeError:
                pass
        return obj

    async def delete(self, request: Request, pks: list) -> int | None:
        for pk in pks:
            obj = await self.find_by_pk(request, pk)
            img = getattr(obj, "image_url", None) if obj else None
            if img and not img.startswith(("http://", "https://")):
                try:
                    (MEDIA_ROOT / img).unlink(missing_ok=True)
                except OSError:
                    pass
        return await super().delete(request, pks)


class EventReferralAdminView(BaseAdminView):
    """Bot deep-link orqali taklif qilinganlar — read-only (chipta manbasi)."""

    name = "Konkurs taklifi"
    label = "Referral: konkurs takliflari"
    icon = "fa fa-share-nodes"

    fields = [
        "id",
        HasOne("event", label="Konkurs", identity="referral-event"),
        HasOne("inviter", label="Taklif qiluvchi", identity="foydalanuvchi"),
        IntegerField("invited_tg_id", label="Taklif qilingan (TG ID)", read_only=True),
        HasOne("invited", label="Taklif qilingan", identity="foydalanuvchi"),
        BooleanField("counted", label="Hisoblangan (chipta)", read_only=True),
        "createdAt",
    ]

    column_list = [
        "id",
        "event",
        "inviter",
        "invited_tg_id",
        "counted",
        "createdAt",
    ]
    column_searchable_list = ["invited_tg_id"]
    column_sortable_list = ["counted", "createdAt"]
    column_filters = ["counted"]
    fields_default_sort = [("createdAt", True)]

    def can_create(self, request: Request) -> bool:
        return False

    def can_edit(self, request: Request) -> bool:
        return False


class ReferralEventParticipantAdminView(BaseAdminView):
    """Referral konkurs ishtirokchilari — read-only."""

    name = "Konkurs ishtirokchisi"
    label = "Referral: konkurs ishtirokchilari"
    icon = "fa fa-users"

    fields = [
        "id",
        HasOne("event", label="Konkurs", identity="referral-event"),
        HasOne("user", label="Foydalanuvchi", identity="foydalanuvchi"),
        IntegerField("number", label="Ishtirokchi №", read_only=True),
        "createdAt",
    ]

    column_list = [
        "id",
        "event",
        "user",
        "number",
        "createdAt",
    ]
    column_searchable_list = ["number"]
    column_sortable_list = ["number", "createdAt"]
    fields_default_sort = [("createdAt", True)]

    def can_create(self, request: Request) -> bool:
        return False

    def can_edit(self, request: Request) -> bool:
        return False


class InviteJoinAdminView(BaseAdminView):
    name = "Qo'shilish (referral)"
    label = "Referral: qo'shilishlar"
    icon = "fa fa-user-plus"

    fields = [
        "id",
        HasOne("invite_link", label="Taklif linki", identity="referral-invite-link"),
        IntegerField("joined_user_tg_id", label="Qo'shilgan foydalanuvchi (Telegram ID)", read_only=True),
        StringField("joined_username", label="Username", read_only=True),
        StringField("joined_full_name", label="Ism-familiya", read_only=True),
        StringField("createdAt", label="Qo'shilgan sana", read_only=True),
        StringField("left_at", label="Tark etgan sana", read_only=True),
        BooleanField("is_counted", label="Hisoblangan", read_only=True),
        StringField("pending_until", label="Grace tugash sanasi", read_only=True),
        StringField("reject_reason", label="Rad etish sababi", read_only=True),
    ]

    column_list = [
        "id",
        "invite_link",
        "joined_user_tg_id",
        "joined_username",
        "joined_full_name",
        "createdAt",
        "left_at",
        "is_counted",
        "pending_until",
        "reject_reason",
    ]
    column_searchable_list = [
        "joined_user_tg_id",
        "joined_username",
        "joined_full_name",
        "reject_reason",
    ]
    column_sortable_list = [
        "createdAt", "left_at", "is_counted", "pending_until"
    ]
    # T-022 · Admin `is_counted` bo'yicha filtrlashi uchun oddiy boolean filter.
    column_filters = ["is_counted"]
    fields_default_sort = [("createdAt", True)]

    def can_create(self, request: Request) -> bool:
        return False

    def can_edit(self, request: Request) -> bool:
        return False
