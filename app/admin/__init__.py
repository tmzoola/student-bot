from pathlib import Path

from admin.auth import AdminAuth
from admin.i18n_uz import install_uzbek
from admin.views.faculty import FacultyAdminView
from admin.views.question import QuestionAdminView
from admin.views.quiz import QuizAdminView
from admin.views.subject import SubjectAdminView
from admin.views.telegram_user import TelegramUserAdminView
from admin.views.topic import TopicAdminView
from db.session import engine
from fastapi import FastAPI
from models.faculty import Faculty
from models.question import Question
from models.quiz import Quiz
from models.subject import Subject
from models.telegram_user import TelegramUser
from models.topic import Topic
from starlette_admin import DropDown
from starlette_admin.contrib.sqla import Admin
from starlette_admin.i18n import I18nConfig

_TEMPLATES_DIR = str(Path(__file__).parent / "templates")


def setup_admin(app: FastAPI) -> None:
    install_uzbek()

    admin = Admin(
        engine,
        title="Student Bot",
        auth_provider=AdminAuth(),
        base_url="/admin/",
        templates_dir=_TEMPLATES_DIR,
        i18n_config=I18nConfig(default_locale="uz", language_header_name=None),
    )

    admin.add_view(DropDown(
        label="Universitet",
        icon="fa fa-graduation-cap",
        views=[
            FacultyAdminView(Faculty, identity="fakultet"),
            SubjectAdminView(Subject, identity="fan"),
        ],
    ))

    admin.add_view(DropDown(
        label="Kontent",
        icon="fa fa-book-open-reader",
        views=[
            TopicAdminView(Topic, identity="mavzu"),
            QuizAdminView(Quiz, identity="test"),
            QuestionAdminView(Question, identity="savol"),
        ],
    ))

    admin.add_view(DropDown(
        label="Foydalanuvchilar",
        icon="fa fa-users",
        views=[TelegramUserAdminView(TelegramUser, identity="foydalanuvchi")],
    ))

    admin.mount_to(app)
