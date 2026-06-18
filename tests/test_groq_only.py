from __future__ import annotations

import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from learny.conversation import ConversationHistory
from learny.groq_client import (
    DEFAULT_GROQ_MODELS,
    DEFAULT_GROQ_TIMEOUT_SECONDS,
    FALLBACK_GROQ_MODEL,
    PRIMARY_GROQ_MODEL,
    SECOND_FALLBACK_GROQ_MODEL,
    THIRD_FALLBACK_GROQ_MODEL,
    GeneratedAnswer,
    GroqAPIError,
    GroqAnswerGenerator,
    parse_generated_answer,
)
from learny.web_server import WebServerConfig, create_handler


EXPECTED_MODELS = (
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "qwen/qwen3-32b",
    "qwen/qwen3.6-27b",
)


class StaticAnswerGenerator:
    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer:
        return GeneratedAnswer(
            answer="Try a quick game, a short walk, or a small coding project.",
            model=PRIMARY_GROQ_MODEL,
        )


class NoAnswerGenerator:
    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer | None:
        return None


class FailingTransport:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def send_chat_completion(self, payload: dict[str, Any], timeout: float) -> str:
        self.calls.append(str(payload["model"]))
        raise GroqAPIError("network down")


class QuestionTransport:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def send_chat_completion(self, payload: dict[str, Any], timeout: float) -> str:
        self.calls.append(str(payload["model"]))
        return "What kind of games?"


class CapturingTransport:
    def __init__(self) -> None:
        self.payload: dict[str, Any] | None = None

    def send_chat_completion(self, payload: dict[str, Any], timeout: float) -> str:
        self.payload = payload
        return "Hello from Groq."


class LearnyGroqOnlyTests(unittest.TestCase):
    def test_exact_model_chain(self) -> None:
        self.assertEqual(DEFAULT_GROQ_MODELS, EXPECTED_MODELS)
        self.assertEqual(PRIMARY_GROQ_MODEL, EXPECTED_MODELS[0])
        self.assertEqual(FALLBACK_GROQ_MODEL, EXPECTED_MODELS[1])
        self.assertEqual(SECOND_FALLBACK_GROQ_MODEL, EXPECTED_MODELS[2])
        self.assertEqual(THIRD_FALLBACK_GROQ_MODEL, EXPECTED_MODELS[3])

    def test_groq_default_timeout_is_capped(self) -> None:
        generator = GroqAnswerGenerator(FailingTransport())

        self.assertEqual(generator.timeout, DEFAULT_GROQ_TIMEOUT_SECONDS)
        self.assertLessEqual(generator.timeout, 12.0)

    def test_transport_failures_try_each_model_once(self) -> None:
        transport = FailingTransport()
        generator = GroqAnswerGenerator(transport)

        self.assertIsNone(generator.generate("why is the sky blue", ConversationHistory()))
        self.assertEqual(transport.calls, list(EXPECTED_MODELS))

    def test_model_questions_are_allowed(self) -> None:
        transport = QuestionTransport()
        generator = GroqAnswerGenerator(transport)

        response = generator.generate("games", ConversationHistory())

        self.assertEqual(
            response,
            GeneratedAnswer(answer="What kind of games?", model=PRIMARY_GROQ_MODEL),
        )
        self.assertEqual(transport.calls, [PRIMARY_GROQ_MODEL])

    def test_groq_payload_uses_plain_answer_mode(self) -> None:
        transport = CapturingTransport()
        generator = GroqAnswerGenerator(transport)
        history = ConversationHistory()
        history.add("who are you", "I'm Learny.")

        response = generator.generate("hello", history)

        self.assertEqual(response, GeneratedAnswer(answer="Hello from Groq.", model=PRIMARY_GROQ_MODEL))
        self.assertIsNotNone(transport.payload)
        assert transport.payload is not None
        self.assertEqual(transport.payload["model"], PRIMARY_GROQ_MODEL)
        self.assertEqual(
            transport.payload["messages"],
            [
                {
                    "role": "system",
                    "content": (
                        "You are Learny, a natural AI assistant. Use the conversation "
                        "when it helps with follow-ups. Return only the text Learny "
                        "should visibly say to the user. Keep answers concise by "
                        "default, but include enough detail to be useful."
                    ),
                },
                {"role": "user", "content": "who are you"},
                {"role": "assistant", "content": "I'm Learny."},
                {"role": "user", "content": "hello"},
            ],
        )

    def test_reasoning_tags_are_removed_from_visible_answer(self) -> None:
        answer = parse_generated_answer("hello", "<think>private notes</think>Hi there.")

        self.assertEqual(answer, "Hi there.")

    def test_status_reports_groq_models_without_storage_fields(self) -> None:
        with run_test_server(StaticAnswerGenerator) as base_url:
            data = get_json(base_url, "/api/status")

        self.assertTrue(data["ok"])
        self.assertTrue(data["groqEnabled"])
        self.assertEqual(tuple(data["models"]), EXPECTED_MODELS)
        self.assertEqual(
            set(data),
            {
                "app",
                "ok",
                "groqEnabled",
                "primaryModel",
                "fallbackModel",
                "secondFallbackModel",
                "thirdFallbackModel",
                "models",
                "unknownMessage",
                "error",
            },
        )

    def test_no_generator_is_not_retryable(self) -> None:
        with run_test_server(lambda: None) as base_url:
            data = post_json(base_url, "/api/ask", {"message": "hello"})

        self.assertEqual(data["source"], "unknown")
        self.assertFalse(data["retryable"])

    def test_generated_answer_comes_from_groq(self) -> None:
        with run_test_server(StaticAnswerGenerator) as base_url:
            data = post_json(base_url, "/api/ask", {"message": "im bored"})

        self.assertEqual(data["source"], "groq")
        self.assertEqual(data["model"], PRIMARY_GROQ_MODEL)
        self.assertFalse(data["retryable"])
        self.assertEqual(data["answer"], "Try a quick game, a short walk, or a small coding project.")
        self.assertEqual(set(data), {"sessionId", "answer", "source", "model", "retryable"})

    def test_failed_generator_chain_is_not_retried_by_browser(self) -> None:
        with run_test_server(NoAnswerGenerator) as base_url:
            data = post_json(base_url, "/api/ask", {"message": "im bored"})

        self.assertEqual(data["source"], "unknown")
        self.assertFalse(data["retryable"])


class run_test_server:
    def __init__(self, generator_factory: Any) -> None:
        self.generator_factory = generator_factory
        self.temp_dir = TemporaryDirectory()
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.base_url = ""

    def __enter__(self) -> str:
        root = Path(self.temp_dir.name)
        config = WebServerConfig(
            static_dir=root,
            generator_factory=self.generator_factory,
        )
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(config))
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self.base_url

    def __exit__(self, *exc_info: object) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5)
        self.temp_dir.cleanup()


def get_json(base_url: str, path: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"{base_url}{path}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
