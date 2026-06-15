from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from learny.bot import DEFAULT_FALLBACK, Learny
from learny.conversation import ConversationHistory
from learny.groq_client import (
    FALLBACK_GROQ_MODEL,
    PRIMARY_GROQ_MODEL,
    GeneratedAnswer,
    GroqAnswerGenerator,
    GroqAPIError,
)
from learny.knowledge import KnowledgeFormatError, parse_knowledge


class PickLast:
    def choice(self, sequence: tuple[str, ...]) -> str:
        return sequence[-1]


class NeverGenerate:
    was_called = False

    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer | None:
        self.was_called = True
        return GeneratedAnswer(
            standalone_question=question,
            answer="Should not be used.",
            model="test",
        )


class StaticGenerate:
    def __init__(self, standalone_question: str, answer: str) -> None:
        self.standalone_question = standalone_question
        self.answer = answer
        self.questions: list[str] = []

    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer | None:
        self.questions.append(question)
        return GeneratedAnswer(
            standalone_question=self.standalone_question,
            answer=self.answer,
            model=PRIMARY_GROQ_MODEL,
        )


class FailingGenerate:
    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer | None:
        return None


class ModelFallbackTransport:
    def __init__(self) -> None:
        self.models: list[str] = []

    def send_chat_completion(self, payload: dict, timeout: float) -> str:
        model = payload["model"]
        self.models.append(model)
        if model == PRIMARY_GROQ_MODEL:
            raise GroqAPIError("primary failed")
        return json.dumps(
            {
                "standalone_question": "what is python",
                "answer": "Python is a programming language.",
            }
        )


class LearnyTests(unittest.TestCase):
    def test_empty_knowledge_has_no_answers(self) -> None:
        bot = Learny(parse_knowledge({"questions": {}}))

        self.assertEqual(bot.answer("anything at all"), DEFAULT_FALLBACK)

    def test_matches_question_inside_user_message(self) -> None:
        bot = Learny(
            parse_knowledge(
                {
                    "questions": {
                        "what is your name": "My name is Learny.",
                    }
                }
            )
        )

        self.assertEqual(
            bot.answer("Hey, WHAT IS YOUR NAME?"),
            "My name is Learny.",
        )

    def test_known_answer_does_not_call_generator(self) -> None:
        generator = NeverGenerate()
        bot = Learny(
            parse_knowledge({"questions": {"hello": "Hello."}}),
            generator=generator,
        )

        self.assertEqual(bot.answer("hello"), "Hello.")
        self.assertFalse(generator.was_called)

    def test_multiple_answers_use_random_choice(self) -> None:
        bot = Learny(
            parse_knowledge(
                {
                    "questions": {
                        "hello": [
                            "Hello.",
                            "Hi.",
                        ],
                    }
                }
            ),
            rng=PickLast(),
        )

        self.assertEqual(bot.answer("please say hello"), "Hi.")

    def test_short_words_do_not_match_inside_longer_words(self) -> None:
        bot = Learny(
            parse_knowledge(
                {
                    "questions": {
                        "hi": "Hi.",
                    }
                }
            )
        )

        self.assertEqual(bot.answer("this should not match"), DEFAULT_FALLBACK)

    def test_longest_question_wins_when_multiple_questions_match(self) -> None:
        bot = Learny(
            parse_knowledge(
                {
                    "questions": {
                        "your name": "Short match.",
                        "what is your name": "Long match.",
                    }
                }
            )
        )

        self.assertEqual(bot.answer("what is your name"), "Long match.")

    def test_list_style_entries_are_supported(self) -> None:
        bot = Learny(
            parse_knowledge(
                {
                    "questions": [
                        {
                            "question": "favorite color",
                            "answers": ["Blue.", "Green."],
                        }
                    ]
                }
            ),
            rng=PickLast(),
        )

        self.assertEqual(bot.answer("what is your favorite color"), "Green.")

    def test_invalid_empty_answer_is_rejected(self) -> None:
        with self.assertRaises(KnowledgeFormatError):
            parse_knowledge({"questions": {"hello": ""}})

    def test_unknown_question_is_generated_saved_and_returned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            knowledge_path = Path(directory) / "knowledge.json"
            knowledge_path.write_text('{"questions": {}}\n', encoding="utf-8")
            generator = StaticGenerate("what is python", "Python is a language.")
            bot = Learny.from_file(knowledge_path, generator=generator)

            self.assertEqual(bot.answer("what is python"), "Python is a language.")
            saved = json.loads(knowledge_path.read_text(encoding="utf-8"))
            self.assertEqual(
                saved["questions"]["what is python"],
                ["Python is a language."],
            )

    def test_follow_up_saves_standalone_question(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            knowledge_path = Path(directory) / "knowledge.json"
            knowledge_path.write_text(
                json.dumps(
                    {
                        "questions": {
                            "tell me about france": "France is a country in Europe."
                        }
                    }
                ),
                encoding="utf-8",
            )
            generator = StaticGenerate(
                "what is the capital of France",
                "The capital of France is Paris.",
            )
            bot = Learny.from_file(knowledge_path, generator=generator)

            self.assertEqual(
                bot.answer("tell me about France"),
                "France is a country in Europe.",
            )
            self.assertEqual(
                bot.answer("what is its capital"),
                "The capital of France is Paris.",
            )
            saved = json.loads(knowledge_path.read_text(encoding="utf-8"))
            self.assertIn("what is the capital of France", saved["questions"])
            self.assertNotIn("what is its capital", saved["questions"])

    def test_unknown_message_is_returned_when_generation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            knowledge_path = Path(directory) / "knowledge.json"
            knowledge_path.write_text('{"questions": {}}\n', encoding="utf-8")
            bot = Learny.from_file(knowledge_path, generator=FailingGenerate())

            self.assertEqual(bot.answer("new question"), DEFAULT_FALLBACK)
            saved = json.loads(knowledge_path.read_text(encoding="utf-8"))
            self.assertEqual(saved, {"questions": {}})

    def test_groq_generator_tries_fallback_model_after_primary_failure(self) -> None:
        transport = ModelFallbackTransport()
        generator = GroqAnswerGenerator(transport)

        generated = generator.generate("what is python", ConversationHistory())

        self.assertIsNotNone(generated)
        self.assertEqual(transport.models, [PRIMARY_GROQ_MODEL, FALLBACK_GROQ_MODEL])
        self.assertEqual(generated.answer, "Python is a programming language.")


if __name__ == "__main__":
    unittest.main()
