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
    GeneratedAnswer,
    GroqAPIError,
    GroqAnswerGenerator,
)
from learny.web_server import WebServerConfig, create_handler


class NoAnswerGenerator:
    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer | None:
        return None


class StaticAnswerGenerator:
    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer:
        return GeneratedAnswer(
            standalone_question="What can I do when bored?",
            answer="Try a quick game, a short walk, or a small coding project.",
            model="fake",
            should_learn=True,
        )


class FailingTransport:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def send_chat_completion(self, payload: dict[str, Any], timeout: float) -> str:
        self.calls.append(str(payload["model"]))
        raise GroqAPIError("network down")


class UnusableTransport:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def send_chat_completion(self, payload: dict[str, Any], timeout: float) -> str:
        self.calls.append(str(payload["model"]))
        return json.dumps(
            {
                "standalone_question": "games",
                "answer": "What kind of games?",
                "should_learn": False,
            }
        )


class LearnyLatencyGuardTests(unittest.TestCase):
    def test_unknown_without_generator_is_not_retryable(self) -> None:
        with run_test_server(lambda: None) as base_url:
            data = post_json(base_url, "/api/ask", {"message": "new unknown thing"})

        self.assertEqual(data["source"], "unknown")
        self.assertFalse(data["retryable"])

    def test_unknown_with_generator_is_retryable(self) -> None:
        with run_test_server(NoAnswerGenerator) as base_url:
            data = post_json(base_url, "/api/ask", {"message": "new unknown thing"})

        self.assertEqual(data["source"], "unknown")
        self.assertTrue(data["retryable"])

    def test_generated_answer_is_not_retryable(self) -> None:
        with run_test_server(StaticAnswerGenerator) as base_url:
            data = post_json(base_url, "/api/ask", {"message": "im bored"})

        self.assertIn(data["source"], {"generated", "knowledge"})
        self.assertEqual(data["answer"], "Try a quick game, a short walk, or a small coding project.")
        self.assertFalse(data["retryable"])

    def test_groq_default_timeout_is_capped(self) -> None:
        generator = GroqAnswerGenerator(FailingTransport())

        self.assertEqual(generator.timeout, DEFAULT_GROQ_TIMEOUT_SECONDS)
        self.assertLessEqual(generator.timeout, 12.0)

    def test_transport_failures_try_each_model_once(self) -> None:
        transport = FailingTransport()
        generator = GroqAnswerGenerator(transport)

        self.assertIsNone(generator.generate("why is the sky blue", ConversationHistory()))
        self.assertEqual(transport.calls, list(DEFAULT_GROQ_MODELS))

    def test_unusable_answers_have_finite_direct_retry(self) -> None:
        transport = UnusableTransport()
        generator = GroqAnswerGenerator(transport)

        self.assertIsNone(generator.generate("games", ConversationHistory()))
        self.assertEqual(len(transport.calls), len(DEFAULT_GROQ_MODELS) * 2)


class run_test_server:
    def __init__(self, generator_factory: Any) -> None:
        self.generator_factory = generator_factory
        self.temp_dir = TemporaryDirectory()
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.base_url = ""

    def __enter__(self) -> str:
        root = Path(self.temp_dir.name)
        knowledge_path = root / "knowledge.json"
        knowledge_path.write_text(
            json.dumps({"questions": {"hello": ["Hi!"]}}),
            encoding="utf-8",
        )
        config = WebServerConfig(
            static_dir=root,
            knowledge_path=knowledge_path,
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
