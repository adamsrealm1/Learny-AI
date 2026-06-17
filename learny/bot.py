from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .conversation import ConversationHistory
from .groq_client import (
    GeneratedAnswer,
    is_prompt_meta_answer,
    is_unusable_generated_answer,
)
from .knowledge import KnowledgeBase, load_knowledge_file
from .learning_rules import is_safe_learned_question
from .memory import remember_answer
from .text import normalize_text


DEFAULT_FALLBACK = "I do not know that yet."
GREETING_FALLBACKS = {
    "hi": "Hi!",
    "hello": "Hello!",
    "hey": "Hey!",
}


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
        known_response = self._reply_from_knowledge(user_message)
        if known_response is not None:
            self.history.add(user_message, known_response.answer)
            return known_response

        generated = self._generate_answer(user_message)
        if generated is None:
            return LearnyResponse(answer=self.fallback, source="unknown")

        if not self._should_remember(generated):
            response = LearnyResponse(
                answer=generated.answer,
                source="generated",
                learned=False,
                model=generated.model,
            )
            self.history.add(user_message, response.answer)
            return response

        self.knowledge = remember_answer(
            self.knowledge_path,
            generated.standalone_question,
            generated.answer,
        )
        learned_response = self._reply_from_knowledge(
            generated.standalone_question,
            learned=True,
            model=generated.model,
        )
        if learned_response is None:
            learned_response = LearnyResponse(
                answer=generated.answer,
                source="knowledge",
                learned=True,
                matched_question=generated.standalone_question,
                model=generated.model,
            )

        self.history.add(user_message, learned_response.answer)
        return learned_response

    def _reply_from_knowledge(
        self,
        user_message: str,
        *,
        learned: bool = False,
        model: str | None = None,
    ) -> LearnyResponse | None:
        match = self.knowledge.best_match(user_message)
        if match is None:
            return None

        answers = tuple(
            answer for answer in match.answers if not is_prompt_meta_answer(answer)
        )
        if not answers:
            return None

        return LearnyResponse(
            answer=self.rng.choice(answers),
            source="knowledge",
            learned=learned,
            matched_question=match.question,
            model=model,
        )

    def _generate_answer(self, user_message: str) -> GeneratedAnswer | None:
        if self.generator is None or self.knowledge_path is None:
            return None

        generated = self.generator.generate(user_message, self.history)
        if generated is None:
            generated = self._fallback_generated_answer(user_message)
            if generated is None:
                return None
        if is_unusable_generated_answer(
            generated.standalone_question,
            generated.answer,
        ):
            return None

        return generated

    def _should_remember(self, generated: GeneratedAnswer) -> bool:
        return (
            self.knowledge_path is not None
            and generated.should_learn
            and is_safe_learned_question(generated.standalone_question)
        )

    def _fallback_generated_answer(self, user_message: str) -> GeneratedAnswer | None:
        normalized = normalize_text(user_message)
        answer = GREETING_FALLBACKS.get(normalized)
        if answer is None:
            return None
        return GeneratedAnswer(
            standalone_question=normalized,
            answer=answer,
            model="local-greeting",
            should_learn=True,
        )
