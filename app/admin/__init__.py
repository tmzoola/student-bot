from pathlib import Path

from admin.auth import AdminAuth
from admin.i18n_uz import install_uzbek
from admin.views.book import BookAdminView
from admin.views.guard import FlaggedUserAdminView, JoinEventAdminView
from admin.views.landing import LandingContentAdminView
from admin.views.menu import MenuSettingsView
from admin.views.module import ModuleAdminView
from admin.views.question import QuestionAdminView
from admin.views.quiz import QuizAdminView
from admin.views.referral import (
    EventReferralAdminView,
    InviteJoinAdminView,
    InviteLinkAdminView,
    ReferralEventAdminView,
    ReferralEventParticipantAdminView,
    RewardTierAdminView,
    TrackedChatAdminView,
    UserRewardAdminView,
)
from admin.views.shop import BookOrderView, ShopBookView, ShopSettingsView
from admin.views.telegram_user import TelegramUserAdminView
from admin.views.topic import TopicAdminView
from db.session import engine
from fastapi import FastAPI
from models.book import Book
from models.guard import FlaggedUser, JoinEvent
from models.landing import LandingContent
from models.menu import MenuSettings
from models.module import Module
from models.question import Question
from models.quiz import Quiz
from models.referral import InviteJoin, InviteLink, TrackedChat
from models.referral_event import (
    EventReferral,
    ReferralEvent,
    ReferralEventParticipant,
)
from models.rewards import RewardTier, UserReward
from models.shop import BookOrder, ShopBook, ShopSettings
from models.telegram_user import TelegramUser
from models.topic import Topic
from starlette_admin import DropDown
from starlette_admin.contrib.sqla import Admin
from starlette_admin.i18n import I18nConfig
from starlette_admin.views import Link

_TEMPLATES_DIR = str(Path(__file__).parent / "templates")


def setup_admin(app: FastAPI) -> None:
    # Register the Uzbek locale before building the admin so its Jinja env and
    # DataTables config pick it up.
    install_uzbek()

    admin = Admin(
        engine,
        title="Muslima Darmonova",
        auth_provider=AdminAuth(),
        base_url="/admin/",
        templates_dir=_TEMPLATES_DIR,
        # Force Uzbek; ignore the browser's Accept-Language so it doesn't flip
        # to en/ru. A language cookie (from the switcher) can still override.
        i18n_config=I18nConfig(default_locale="uz", language_header_name=None),
    )

    # ── Kontent (o'quv materiallari) ───────────────────────────────
    admin.add_view(DropDown(always_open=False, 
        label="Kontent",
        icon="fa fa-book-open-reader",
        views=[
            Link(label="Test yaratish", icon="fa fa-wand-magic-sparkles",
                 url="/admin-tools/builder"),
            Link(label="Excel orqali test", icon="fa fa-file-excel",
                 url="/admin-tools/quiz-import"),
            Link(label="Kitob yuklash", icon="fa fa-file-arrow-up",
                 url="/admin-tools/books"),
            ModuleAdminView(Module, identity="modul"),
            QuizAdminView(Quiz, identity="test"),
            QuestionAdminView(Question, identity="savol"),
            BookAdminView(Book, identity="kitob"),
        ],
    ))

    # ── Musobaqalar va reyting ─────────────────────────────────────
    admin.add_view(DropDown(always_open=False, 
        label="Musobaqalar",
        icon="fa fa-trophy",
        views=[
            Link(label="Yutuqli testlar", icon="fa fa-trophy",
                 url="/admin-tools/contests"),
            Link(label="Reyting", icon="fa fa-ranking-star",
                 url="/admin-tools/leaderboard"),
        ],
    ))

    # ── Foydalanuvchilar bilan aloqa ───────────────────────────────
    admin.add_view(DropDown(always_open=False, 
        label="Foydalanuvchilar",
        icon="fa fa-users",
        views=[
            TelegramUserAdminView(TelegramUser, identity="foydalanuvchi"),
            Link(label="Xabar yuborish", icon="fa fa-bullhorn",
                 url="/admin-tools/broadcast"),
            Link(label="Motivatsiya", icon="fa fa-quote-left",
                 url="/admin-tools/quotes"),
        ],
    ))

    # ── Do'kon ─────────────────────────────────────────────────────
    admin.add_view(DropDown(always_open=False, 
        label="Do'kon",
        icon="fa fa-store",
        views=[
            Link(label="Do'kon kitoblari", icon="fa fa-book-open",
                 url="/admin-tools/shop-books"),
            Link(label="Buyurtmalar boshqaruvi", icon="fa fa-box-open",
                 url="/admin-tools/orders"),
            ShopSettingsView(ShopSettings, identity="dokon-sozlama"),
            ShopBookView(ShopBook, identity="dokon-kitob"),
            BookOrderView(BookOrder, identity="buyurtma"),
        ],
    ))

    # ── Referral tizimi ────────────────────────────────────────────
    admin.add_view(DropDown(always_open=False, 
        label="Referral",
        icon="fa fa-user-plus",
        views=[
            Link(label="Konkurs g'oliblari", icon="fa fa-trophy",
                 url="/admin-tools/event-leaderboard"),
            Link(label="Top inviterlar", icon="fa fa-medal",
                 url="/admin-tools/referral-leaderboard"),
            ReferralEventAdminView(ReferralEvent, identity="referral-event"),
            ReferralEventParticipantAdminView(
                ReferralEventParticipant, identity="referral-event-participant"
            ),
            EventReferralAdminView(
                EventReferral, identity="referral-event-referral"
            ),
            TrackedChatAdminView(TrackedChat, identity="referral-tracked-chat"),
            InviteLinkAdminView(InviteLink, identity="referral-invite-link"),
            InviteJoinAdminView(InviteJoin, identity="referral-invite-join"),
            RewardTierAdminView(RewardTier, identity="referral-reward-tier"),
            UserRewardAdminView(UserReward, identity="referral-user-reward"),
        ],
    ))

    # ── Guruh guard boti ───────────────────────────────────────────
    admin.add_view(DropDown(always_open=False, 
        label="Guard",
        icon="fa fa-shield-halved",
        views=[
            JoinEventAdminView(JoinEvent, identity="guard-qoshilish"),
            FlaggedUserAdminView(FlaggedUser, identity="guard-ogohlantirish"),
        ],
    ))

    # ── Sayt sozlamalari ───────────────────────────────────────────
    admin.add_view(DropDown(always_open=False, 
        label="Sozlamalar",
        icon="fa fa-gear",
        views=[
            LandingContentAdminView(LandingContent, identity="bosh-sahifa-matni"),
            MenuSettingsView(MenuSettings, identity="menyu-sozlama"),
        ],
    ))

    admin.mount_to(app)
