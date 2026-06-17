from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .conversation import ConversationHistory
from .groq_client import GeneratedAnswer, is_prompt_meta_answer


DEFAULT_FALLBACK = "Something went wrong. Try again later."


class AnswerGenerator(Protocol):
    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer | None:
        """Generate Learny's answer for a user message."""


@dataclass(frozen=True)
class LearnyResponse:
    answer: str
    source: str
    model: str | None = None


class Learny:
    """Groq-only chatbot with session conversation context."""

    def __init__(
        self,
        *,
        generator: AnswerGenerator | None,
        history: ConversationHistory | None = None,
        fallback: str = DEFAULT_FALLBACK,
    ) -> None:
        self.generator = generator
        self.history = history or ConversationHistory()
        self.fallback = fallback

    def answer(self, user_message: str) -> str:
        return self.reply(user_message).answer

    def reply(self, user_message: str) -> LearnyResponse:
        if self.generator is None:
            return LearnyResponse(answer=self.fallback, source="unknown")

        generated = self.generator.generate(user_message, self.history)
        if generated is None or is_prompt_meta_answer(generated.answer):
            return LearnyResponse(answer=self.fallback, source="unknown")

        response = LearnyResponse(
            answer=generated.answer,
            source="groq",
            model=generated.model,
        )
        self.history.add(user_message, response.answer)
        return response
