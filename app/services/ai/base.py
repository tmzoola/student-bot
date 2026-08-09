"""AI provider ABC."""
from __future__ import annotations

from abc import ABC, abstractmethod

from services.ai.schemas import QuizGenResult


class AIProvider(ABC):
    @abstractmethod
    async def generate_quiz(
        self,
        text: str,
        num_questions: int = 10,
        difficulty: str = "medium",
        language: str = "uz",
    ) -> QuizGenResult:
        """Berilgan matndan MCQ testlar to'plamini yaratadi."""


class AIProviderError(Exception):
    """AI chaqiruvi muvaffaqiyatsiz tugadi."""
