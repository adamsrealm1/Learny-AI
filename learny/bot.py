from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .conversation import ConversationHistory
from .groq_client import GeneratedAnswer
from .knowledge import KnowledgeBase, load_knowledge_file
from .memory import remember_answer


DEFAULT_FALLBACK = (
    "I do not know that yet. Add it to data/knowledge.json and ask again."
)


class RandomChooser(Protocol):
    def choice(self, sequence: tuple[str, ...]) -> str:
        """Return one item from a non-empty sequence."""


class AnswerGenerator(Protocol):
    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer | None:
        """Generate an answer for a question Learny does not know yet."""


@dataclass(frozen=True)
class LearnyResponse:
    answer: str
    source: str
    learned: bool = False
    matched_question: str | None = None
    model: str | None = None


class Learny:
    """Small chatbot that checks local knowledge before optional API learning."""

    def __init__(
        self,
        knowledge: KnowledgeBase,
        *,
        knowledge_path: str | Path | None = None,
        generator: AnswerGenerator | None = None,
        history: ConversationHistory | None = None,
        rng: RandomChooser | None = None,
        fallback: str = DEFAULT_FALLBACK,
    ) -> None:
        self.knowledge = knowledge
        self.knowledge_path = Path(knowledge_path) if knowledge_path is not None else None
        self.generator = generator
        self.history = history or ConversationHistory()
        self.rng = rng or random.SystemRandom()
        self.fallback = fallback

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        generator: AnswerGenerator | None = None,
        history: ConversationHistory | None = None,
        rng: RandomChooser | None = None,
        fallback: str = DEFAULT_FALLBACK,
    ) -> "Learny":
        return cls(
            load_knowledge_file(path),
            knowledge_path=path,
            generator=generator,
            history=history,
            rng=rng,
            fallback=fallback,
        )

    def answer(self, user_message: str) -> str:
        return self.reply(user_message).answer

    def reply(self, user_message: str) -> LearnyResponse:
        match = self.knowledge.best_match(user_message)
        if match is not None:
            answer = self.rng.choice(match.answers)
            self.history.add(user_message, answer)
            return LearnyResponse(
                answer=answer,
                source="knowledge",
                matched_question=match.question,
            )

        generated = self._learn_answer(user_message)
        if generated is None:
            return LearnyResponse(answer=self.fallback, source="unknown")

        self.history.add(user_message, generated.answer)
        return LearnyResponse(
            answer=generated.answer,
            source="groq",
            learned=True,
            matched_question=generated.standalone_question,
            model=generated.model,
        )

    def _learn_answer(self, user_message: str) -> GeneratedAnswer | None:
        if self.generator is None or self.knowledge_path is None:
            return None

        generated = self.generator.generate(user_message, self.history)
        if generated is None:
            return None

        self.knowledge = remember_answer(
            self.knowledge_path,
            generated.standalone_question,
            generated.answer,
        )
        return generated
