import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)
from sqlalchemy import select

from core.config import MEDIA_ROOT, settings
from db.session import session_factory
from models.shop import BookOrder, OrderStatus, ShopBook, ShopSettings
from models.telegram_user import TelegramUser
from services.referral.events import (
    announcement_keyboard,
    get_active_event,
    normalize_newlines,
    record_referral,
)

_TZ = ZoneInfo("Asia/Tashkent")

logger = logging.getLogger(__name__)
router = Router()


class Register(StatesGroup):
    phone = State()
    full_name = State()


class ChangeName(StatesGroup):
    full_name = State()


class BookDelivery(StatesGroup):
    name = State()
    phone = State()
    address = State()


# O'zbekiston mobil raqamlari uchun: +998 XX XXX XX XX yoki XX XXX XX XX
# Operator kodlari: 9X (90–99), 33, 55, 77, 88
PHONE_RE = re.compile(
    r"^(\+?998)?\s?(9[0-9]|33|55|77|88)\s?\d{3}\s?\d{2}\s?\d{2}$"
)


async def get_or_create_user(tg_user) -> TelegramUser:
    async with session_factory() as session:
        stmt = select(TelegramUser).where(TelegramUser.telegram_id == tg_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        now = datetime.now(_TZ)
        if not user:
            user = TelegramUser(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                language_code=tg_user.language_code,
                last_active_at=now,
            )
            session.add(user)
        else:
            # Refresh at most once per hour to avoid excessive writes.
            if not user.last_active_at or (now - user.last_active_at).total_seconds() > 3600:
                user.last_active_at = now
        await session.commit()
        await session.refresh(user)
        return user


async def _update_user(telegram_id: int, **fields) -> TelegramUser | None:
    async with session_factory() as session:
        result = await session.execute(
            select(TelegramUser).where(TelegramUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None
        for k, v in fields.items():
            setattr(user, k, v)
        await session.commit()
        await session.refresh(user)
        return user


async def _get_menu_settings():
    from models.menu import MenuSettings
    async with session_factory() as session:
        r = await session.execute(select(MenuSettings).limit(1))
        return r.scalar_one_or_none()


async def _main_keyboard(tg_id: int):
    """Asosiy menyu (reply keyboard). Qaysi tugma ko'rinishi admin paneldagi
    `MenuSettings` bilan boshqariladi (yo'q bo'lsa hammasi ko'rsatiladi)."""
    from api.v1.webapp import make_bot_token
    token = make_bot_token(tg_id)
    s = await _get_menu_settings()
    show_test = s.show_test if s else True
    show_books = s.show_books if s else True
    show_info = s.show_info if s else True
    show_referral = s.show_referral if s else True

    rows: list[list[KeyboardButton]] = []
    if show_test:
        rows.append([KeyboardButton(
            text="🎓 Test ishlash",
            web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/webapp/?t={token}"),
        )])
    second: list[KeyboardButton] = []
    if show_books:
        second.append(KeyboardButton(text="📚 Kitoblar do'koni"))
    if show_info:
        second.append(KeyboardButton(text="ℹ️ Ma'lumot"))
    if second:
        rows.append(second)
    if show_referral:
        rows.append([KeyboardButton(text="🔗 Taklif linki")])

    if not rows:
        # Barcha tugma o'chirilgan — klaviaturani olib tashlaymiz.
        return ReplyKeyboardRemove()
    return ReplyKeyboardMarkup(
        keyboard=rows, resize_keyboard=True, is_persistent=True
    )


def _contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def _show_main_menu(msg: Message, user: TelegramUser) -> None:
    name = user.first_name or user.username or "Foydalanuvchi"
    text = (
        f"Assalomu alaykum, <b>{name}</b>! 👋\n\n"
        "📚 <b>Muslima Darmonova</b> — bu sizning shaxsiy imtihon tayyorgarlik yordamchingiz.\n\n"
        "✅ Mavzular va bo'limlar bo'yicha test yechish\n"
        "📊 Natijalaringizni kuzating\n"
        "🏆 O'z ko'rsatkichlaringizni yaxshilang\n\n"
        "👇 Quyidagi tugmalar orqali boshlang!"
    )
    await msg.answer(text, reply_markup=await _main_keyboard(user.telegram_id))


def _resolve_photo(image_url: str | None):
    """Saqlangan rasmni `answer_photo` uchun tayyorlaydi (URL yoki lokal fayl).

    - Bo'sh bo'lsa None.
    - http(s):// bilan boshlansa — URL string o'zi.
    - `/media/...`, `media/...` yoki nisbiy yo'l — MEDIA_ROOT ichidagi lokal
      fayl `FSInputFile` sifatida (Telegram nisbiy URL'ni qabul qilmaydi).
    """
    if not image_url:
        return None
    if image_url.startswith(("http://", "https://")):
        return image_url
    rel = image_url.lstrip("/")
    if rel.startswith("media/"):
        rel = rel[len("media/"):]
    path = MEDIA_ROOT / rel
    if path.exists():
        return FSInputFile(str(path))
    logger.warning("rasm topilmadi: %s", path)
    return None


async def _maybe_show_event(msg: Message) -> bool:
    """Faol referral event bo'lsa e'lonni ko'rsatadi. True — ko'rsatildi.

    E'lon: rasm (bor bo'lsa) + matn + inline kanal/guruh tugmalari va
    "✅ Obuna bo'ldim". So'ng asosiy reply keyboard qayta o'rnatiladi, shunda
    Test/Kitoblar/Ma'lumot/Taklif linki tugmalari o'zgarishsiz qoladi.
    """
    now = datetime.now(_TZ)
    async with session_factory() as session:
        event = await get_active_event(session, now)
        if event is None:
            return False

    kb = announcement_keyboard(
        msg.from_user.id, event.share_text or event.announcement_text
    )
    caption = re.sub(r"\n{3,}", "\n\n", normalize_newlines(event.announcement_text))
    photo = _resolve_photo(event.image_url)
    if photo is not None:
        try:
            await msg.answer_photo(photo, caption=caption, reply_markup=kb)
        except Exception:
            logger.exception("event rasmini yuborib bo'lmadi: event_id=%s", event.id)
            await msg.answer(caption, reply_markup=kb)
    else:
        await msg.answer(caption, reply_markup=kb)

    # Asosiy menyu tugmalarini (reply keyboard) qayta o'rnatamiz.
    await msg.answer(
        "👇 Quyidagi tugmalar orqali boshlang!",
        reply_markup=await _main_keyboard(msg.from_user.id),
    )
    return True


@router.message(CommandStart())
async def start_handler(msg: Message, state: FSMContext, command: CommandObject):
    # Referral/konkurs oqimi faqat shaxsiy chatda ishlaydi. Guruh/kanalда a'zolar
    # deep-link bosganda Telegram `/start@bot` ni guruhga yuboradi — bu foydasiz
    # clutter. Bot admin bo'lsa o'sha buyruq xabarini o'chiramiz; javob yozmaymiz.
    if msg.chat.type != "private":
        try:
            await msg.delete()
        except Exception:  # noqa: BLE001 — o'chirish huquqi yo'q bo'lishi mumkin
            pass
        return
    await state.clear()
    user = await get_or_create_user(msg.from_user)

    # /start ref_<inviter_tg_id> — deep-link orqali kelgan taklif.
    # Faol event bo'lsa kutilayotgan referral yoziladi; taklif qilingan
    # foydalanuvchi obuna gate'dan o'tgach chipta sifatida hisoblanadi.
    args = (command.args or "").strip()
    if args.startswith("ref_") and args[4:].isdigit():
        inviter_tg_id = int(args[4:])
        now = datetime.now(_TZ)
        async with session_factory() as session:
            event = await get_active_event(session, now)
            if event is not None:
                await record_referral(
                    session,
                    event_id=event.id,
                    inviter_tg_id=inviter_tg_id,
                    invited_tg_id=msg.from_user.id,
                )

    if not user.is_registered:
        await msg.answer(
            "👋 Xush kelibsiz!\n\n"
            "Ro'yxatdan o'tish uchun avval telefon raqamingizni yuboring.",
            reply_markup=_contact_keyboard(),
        )
        await state.set_state(Register.phone)
        return

    if await _maybe_show_event(msg):
        return

    await _show_main_menu(msg, user)


@router.message(Register.phone, F.contact)
async def register_phone_contact(msg: Message, state: FSMContext):
    if msg.contact.user_id and msg.contact.user_id != msg.from_user.id:
        await msg.answer("Iltimos, o'zingizning raqamingizni yuboring.")
        return
    await state.update_data(phone=msg.contact.phone_number)
    await msg.answer(
        "✅ Raqam qabul qilindi.\n\nEndi <b>Ism Familyangizni</b> kiriting:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(Register.full_name)


@router.message(Register.phone)
async def register_phone_text(msg: Message, state: FSMContext):
    text = (msg.text or "").strip()
    if not PHONE_RE.match(text):
        await msg.answer(
            "Telefon raqam noto'g'ri. Iltimos, «📱 Raqamni yuborish» tugmasidan foydalaning "
            "yoki raqamni +998XXXXXXXXX formatida yuboring.",
            reply_markup=_contact_keyboard(),
        )
        return
    await state.update_data(phone=text)
    await msg.answer(
        "✅ Raqam qabul qilindi.\n\nEndi <b>Ism Familyangizni</b> kiriting:",
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(Register.full_name)


@router.message(Register.full_name)
async def register_full_name(msg: Message, state: FSMContext):
    text = (msg.text or "").strip()
    if len(text) < 2 or len(text) > 100:
        await msg.answer("Ism Familya 2 dan 100 gacha belgi bo'lishi kerak. Qayta kiriting:")
        return

    parts = text.split(maxsplit=1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else None

    data = await state.get_data()
    user = await _update_user(
        msg.from_user.id,
        phone=data.get("phone"),
        first_name=first_name,
        last_name=last_name,
    )
    await state.clear()

    if not user:
        await msg.answer("Xatolik yuz berdi. /start ni bosing.")
        return

    await msg.answer("🎉 Ro'yxatdan o'tdingiz!")

    # Aktiv referral konkurs bo'lsa e'londan avval ko'rsatamiz — yangi
    # foydalanuvchi /start ni ikkinchi marta bosishga majbur bo'lmasin.
    if await _maybe_show_event(msg):
        return
    await _show_main_menu(msg, user)


@router.message(Command("settings"))
async def settings_handler(msg: Message, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(msg.from_user)

    if not user.is_registered:
        await msg.answer("Avval ro'yxatdan o'ting: /start")
        return

    full = " ".join(filter(None, [user.first_name, user.last_name])) or "—"
    phone = user.phone or "—"
    text = (
        "⚙️ <b>Sozlamalar</b>\n\n"
        f"👤 Ism Familya: <b>{full}</b>\n"
        f"📱 Telefon: <b>{phone}</b>\n\n"
        "Ismni o'zgartirish uchun /change_name buyrug'ini yuboring "
        "yoki quyidagi tugma orqali WebApp sozlamalarini oching."
    )
    from api.v1.webapp import make_bot_token
    _tok = make_bot_token(msg.from_user.id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚙️ WebApp sozlamalari",
                    web_app=WebAppInfo(url=f"{settings.WEBAPP_URL}/webapp/settings?t={_tok}"),
                )
            ]
        ]
    )
    await msg.answer(text, reply_markup=kb)


@router.message(Command("change_name"))
async def change_name_start(msg: Message, state: FSMContext):
    user = await get_or_create_user(msg.from_user)
    if not user.is_registered:
        await msg.answer("Avval ro'yxatdan o'ting: /start")
        return
    await msg.answer("Yangi <b>Ism Familyangizni</b> kiriting:")
    await state.set_state(ChangeName.full_name)


@router.message(ChangeName.full_name)
async def change_name_apply(msg: Message, state: FSMContext):
    text = (msg.text or "").strip()
    if len(text) < 2 or len(text) > 100:
        await msg.answer("Ism Familya 2 dan 100 gacha belgi bo'lishi kerak. Qayta kiriting:")
        return
    parts = text.split(maxsplit=1)
    first_name = parts[0]
    last_name = parts[1] if len(parts) > 1 else None

    await _update_user(msg.from_user.id, first_name=first_name, last_name=last_name)
    await state.clear()
    await msg.answer(f"✅ Ism yangilandi: <b>{text}</b>")


# ─── Main menu button handlers ────────────────────────────────────────────

@router.message(F.text == "📚 Kitoblar do'koni")
async def vip_handler(msg: Message):
    books = await _get_active_books()
    if not books:
        await msg.answer(
            "📚 <b>Kitoblar do'koni</b>\n\nHozircha yangi kitoblar qo'shilmoqda. Tez kunda!\n\n"
            "Yangiliqlardan xabardor bo'lish uchun botda qoling. 🔔"
        )
        return
    await msg.answer(
        "📚 <b>Kitoblar do'koni</b>\n\nMavjud kitoblarni ko'rish uchun tugmani bosing 👇",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"📖 {b.title} — {_fmt_price(b.price)}",
                    callback_data=f"book_info:{b.id}",
                )]
                for b in books
            ]
        ),
    )


@router.message(F.text == "ℹ️ Ma'lumot")
async def info_handler(msg: Message):
    await msg.answer(
        "ℹ️ <b>Muslima Darmonova haqida</b>\n\n"
        "🎓 Attestatsiyaga tayyorgarlik platformasi\n\n"
        "✅ Mavzular bo'yicha testlar\n"
        "🏆 Yutuqli kontestlar\n"
        "📊 Shaxsiy reyting va tahlil\n"
        "📚 Attestatsiyaga oid kitoblar\n\n"
        "📞 Murojaat uchun: @m_darmonova\n"
        "📚 Kitob admini: @attestatsiya_kitob\n\n"
        "🚀 Test ishlash uchun pastdagi tugmani bosing!",
        reply_markup=await _main_keyboard(msg.from_user.id),
    )


# ─── Shop / Book ordering ─────────────────────────────────────────────────

def _fmt_price(price: int) -> str:
    return f"{price:,}".replace(",", " ") + " so'm"


async def _get_shop_settings() -> ShopSettings | None:
    async with session_factory() as s:
        r = await s.execute(select(ShopSettings).limit(1))
        return r.scalar_one_or_none()


async def _get_active_books() -> list[ShopBook]:
    async with session_factory() as s:
        r = await s.execute(
            select(ShopBook).where(ShopBook.is_active == True).order_by(ShopBook.order, ShopBook.id)  # noqa: E712
        )
        return list(r.scalars().all())


@router.message(Command("kitoblar"))
async def shop_books_handler(msg: Message):
    books = await _get_active_books()
    if not books:
        await msg.answer("Hozircha sotuvdagi kitoblar yo'q. 📚")
        return

    await msg.answer(
        "📚 <b>Muslima Darmonova do'koni</b>\n\nMavjud kitoblar:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"📖 {b.title} — {_fmt_price(b.price)}",
                    callback_data=f"book_info:{b.id}",
                )]
                for b in books
            ]
        ),
    )


@router.callback_query(F.data.startswith("book_info:"))
async def book_info_callback(cb: CallbackQuery):
    book_id = int(cb.data.split(":")[1])
    async with session_factory() as s:
        book = await s.get(ShopBook, book_id)
    if not book or not book.is_active:
        await cb.answer("Kitob topilmadi", show_alert=True)
        return

    desc = book.description or ""
    text = (
        f"📖 <b>{book.title}</b>\n\n"
        + (f"{desc}\n\n" if desc else "")
        + f"💰 <b>Narxi: {_fmt_price(book.price)}</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛒 Sotib olish", callback_data=f"buy_book:{book_id}"),
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="back_to_books"),
    ]])

    cover = _resolve_photo(book.cover_image_url)
    if cover is not None:
        try:
            await cb.message.answer_photo(cover, caption=text, reply_markup=kb)
        except Exception:
            logger.exception("kitob rasmini yuborib bo'lmadi: book_id=%s", book_id)
            await cb.message.answer(text, reply_markup=kb)
    else:
        await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data.in_({"back_to_books", "show_shop"}))
async def back_to_books(cb: CallbackQuery):
    await cb.answer()
    await shop_books_handler(cb.message)


@router.callback_query(F.data.startswith("buy_book:"))
async def buy_book_callback(cb: CallbackQuery):
    book_id = int(cb.data.split(":")[1])
    settings_row = await _get_shop_settings()
    if not settings_row or not settings_row.card_number:
        await cb.answer("Do'kon hozircha ishlamayapti. Iltimos, keyinroq urinib ko'ring.", show_alert=True)
        return

    async with session_factory() as s:
        book = await s.get(ShopBook, book_id)
        if not book or not book.is_active:
            await cb.answer("Kitob topilmadi", show_alert=True)
            return
        # Find user record
        from sqlalchemy import select as sel_
        r = await s.execute(sel_(TelegramUser).where(TelegramUser.telegram_id == cb.from_user.id))
        user = r.scalar_one_or_none()
        if not user:
            await cb.answer("Avval /start yuboring", show_alert=True)
            return
        order = BookOrder(user_id=user.id, book_id=book_id, status=OrderStatus.PENDING)
        s.add(order)
        await s.commit()
        await s.refresh(order)
        order_id = order.id
        book_title = book.title
        book_price = book.price

    card = settings_row.card_number or "—"
    holder = settings_row.card_holder or "—"
    admin_un = settings_row.admin_username or "admin"

    await cb.message.answer(
        f"🛒 <b>Buyurtma #{order_id} yaratildi!</b>\n\n"
        f"📖 Kitob: <b>{book_title}</b>\n"
        f"💰 Narxi: <b>{_fmt_price(book_price)}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💳 <b>To'lov ma'lumotlari:</b>\n"
        f"Karta: <code>{card}</code>\n"
        f"Egasi: <b>{holder}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ To'lovni amalga oshirgach, <b>skrinshtotni @{admin_un} ga yuboring</b>.\n"
        f"📝 Xabarda buyurtma raqamingizni ko'rsating: <b>#{order_id}</b>\n\n"
        "Tasdiqlangach sizga xabar yuboriladi! ⏳",
    )
    await cb.answer("Buyurtma yaratildi!")


# ─── Delivery info FSM (triggered by admin confirm action) ───────────────

@router.message(BookDelivery.name)
async def delivery_name(msg: Message, state: FSMContext):
    text = (msg.text or "").strip()
    if len(text) < 2:
        await msg.answer("Iltimos, to'liq Ism Familyangizni kiriting:")
        return
    await state.update_data(d_name=text)
    await state.set_state(BookDelivery.phone)
    await msg.answer("📱 Telefon raqamingizni kiriting (+998XXXXXXXXX):")


@router.message(BookDelivery.phone)
async def delivery_phone(msg: Message, state: FSMContext):
    text = (msg.text or "").strip()
    if not PHONE_RE.match(text):
        await msg.answer("Noto'g'ri format. Iltimos, telefon raqamingizni kiriting (+998XXXXXXXXX):")
        return
    await state.update_data(d_phone=text)
    await state.set_state(BookDelivery.address)
    await msg.answer("🏠 Yashash manzilingizni to'liq kiriting\n(viloyat, shahar/tuman, ko'cha, uy):")


@router.message(BookDelivery.address)
async def delivery_address(msg: Message, state: FSMContext):
    text = (msg.text or "").strip()
    if len(text) < 5:
        await msg.answer("Iltimos, to'liq manzilingizni kiriting:")
        return

    data = await state.get_data()
    order_id = data.get("order_id")
    await state.clear()

    if order_id:
        async with session_factory() as s:
            order = await s.get(BookOrder, int(order_id))
            if order:
                order.delivery_name = data.get("d_name")
                order.delivery_phone = data.get("d_phone")
                order.delivery_address = text
                order.status = OrderStatus.PROCESSING
                await s.commit()

    await msg.answer(
        "✅ <b>Ma'lumotlaringiz qabul qilindi!</b>\n\n"
        "📦 Kitobingiz tez kunda sizga yuboriladi.\n"
        "Yetkazib berish jarayonini <b>WebApp</b>da kuzatishingiz mumkin. 🚚",
    )
