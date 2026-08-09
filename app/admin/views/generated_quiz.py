from admin.views.base import BaseAdminView
from models.generated_quiz import QuizDifficulty
from models.question import CorrectOption
from starlette_admin import (
    EnumField,
    HasOne,
    IntegerField,
    StringField,
    TextAreaField,
)


class GeneratedQuizAdminView(BaseAdminView):
    name = "AI Test"
    label = "AI Testlar"
    icon = "fa fa-robot"

    fields = [
        "id",
        HasOne("material", label="Material", identity="material"),
        HasOne("student_profile", label="Talaba", identity="talaba-profili"),
        StringField("title", label="Sarlavha"),
        EnumField("difficulty", label="Qiyinlik", enum=QuizDifficulty),
        StringField("language", label="Til"),
        IntegerField("num_questions", label="Savollar soni"),
    ]

    column_list = [
        "id", "title", "material", "difficulty",
        "num_questions", "createdAt",
    ]
    column_sortable_list = ["difficulty", "num_questions", "createdAt"]


class GeneratedQuestionAdminView(BaseAdminView):
    name = "AI Savol"
    label = "AI Savollar"
    icon = "fa fa-circle-question"

    fields = [
        "id",
        HasOne("generated_quiz", label="Test", identity="ai-test"),
        IntegerField("order", label="Tartib"),
        TextAreaField("text", label="Savol"),
        StringField("option_a", label="A"),
        StringField("option_b", label="B"),
        StringField("option_c", label="C"),
        StringField("option_d", label="D"),
        EnumField("correct_option", label="To'g'ri", enum=CorrectOption),
        TextAreaField("explanation", label="Tushuntirish"),
    ]

    column_list = ["id", "generated_quiz", "order", "text", "correct_option"]
