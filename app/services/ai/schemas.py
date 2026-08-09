"""AI generatsiya natijasi uchun Pydantic sxemalar."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

CorrectLetter = Literal["A", "B", "C", "D"]


class GeneratedQuestionData(BaseModel):
    text: str = Field(min_length=5, max_length=2000)
    option_a: str = Field(min_length=1, max_length=1024)
    option_b: str = Field(min_length=1, max_length=1024)
    option_c: str = Field(min_length=1, max_length=1024)
    option_d: str = Field(min_length=1, max_length=1024)
    correct_option: CorrectLetter
    explanation: str | None = Field(default=None, max_length=2000)

    @field_validator("correct_option", mode="before")
    @classmethod
    def _upper(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().upper()
        return v


class QuizGenResult(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    questions: list[GeneratedQuestionData] = Field(min_length=1, max_length=50)
    input_tokens: int = 0
    output_tokens: int = 0
