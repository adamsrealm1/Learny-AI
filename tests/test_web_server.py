from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path

from learny.bot import DEFAULT_FALLBACK
from learny.groq_client import GeneratedAnswer, PRIMARY_GROQ_MODEL
from learny.messages import GENERIC_ERROR_MESSAGE
from learny.web_server import WebServerConfig, create_handler


class StaticGenerate:
    def generate(self, question, history):
        return GeneratedAnswer(
            standalone_question="what is web learny",
            answer="Web Learny is running through the Python server.",
            model=PRIMARY_GROQ_MODEL,
        )


class WebServerTests(unittest.TestCase):
    def test_status_and_known_answer_api(self) -> None:
        with running_test_server({"questions": {"hello": "Hello from JSON."}}) as base_url:
            status = request_json(f"{base_url}/api/status")
            answer = request_json(
                f"{base_url}/api/ask",
                {"message": "please say hello"},
            )

        self.assertEqual(status["knowledgeCount"], 1)
        self.assertFalse(status["groqEnabled"])
        self.assertEqual(answer["answer"], "Hello from JSON.")
        self.assertEqual(answer["source"], "knowledge")
        self.assertFalse(answer["learned"])

    def test_unknown_question_returns_unknown_message_without_generator(self) -> None:
        with running_test_server({"questions": {}}) as base_url:
            answer = request_json(
                f"{base_url}/api/ask",
                {"message": "something new"},
            )

        self.assertEqual(answer["answer"], DEFAULT_FALLBACK)
        self.assertEqual(answer["source"], "unknown")

    def test_web_api_saves_generated_answer(self) -> None:
        with running_test_server(
            {"questions": {}},
            generator_factory=StaticGenerate,
        ) as base_url:
            answer = request_json(
                f"{base_url}/api/ask",
                {"message": "what is web learny"},
            )
            knowledge = request_json(f"{base_url}/api/knowledge")

        self.assertEqual(
            answer["answer"],
            "Web Learny is running through the Python server.",
        )
        self.assertTrue(answer["learned"])
        self.assertEqual(answer["model"], PRIMARY_GROQ_MODEL)
        self.assertEqual(knowledge["count"], 1)
        self.assertEqual(knowledge["questions"][0]["question"], "what is web learny")

    def test_visible_errors_use_generic_message(self) -> None:
        with running_test_server({"questions": {"hello": "Hello from JSON."}}) as base_url:
            status, api_error = request_json_with_status(
                f"{base_url}/api/ask",
                {"message": ""},
            )
            missing_status, missing_text = request_text_with_status(f"{base_url}/missing")

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(api_error["error"], GENERIC_ERROR_MESSAGE)
        self.assertEqual(missing_status, HTTPStatus.NOT_FOUND)
        self.assertEqual(missing_text, GENERIC_ERROR_MESSAGE)


class running_test_server:
    def __init__(self, knowledge, generator_factory=lambda: None):
        self.knowledge = knowledge
        self.generator_factory = generator_factory
        self.directory = tempfile.TemporaryDirectory()
        self.server = None
        self.thread = None
        self.base_url = ""

    def __enter__(self):
        root = Path(self.directory.name)
        static_dir = root / "web"
        static_dir.mkdir()
        (static_dir / "index.html").write_text("<!doctype html><title>test</title>")
        knowledge_path = root / "knowledge.json"
        knowledge_path.write_text(json.dumps(self.knowledge), encoding="utf-8")

        config = WebServerConfig(
            static_dir=static_dir,
            knowledge_path=knowledge_path,
            generator_factory=self.generator_factory,
        )
        handler = create_handler(config)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self.base_url

    def __exit__(self, exc_type, exc, traceback):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5)
        self.directory.cleanup()


def request_json(url: str, payload: dict | None = None) -> dict:
    status, body = request_json_with_status(url, payload)
    if status >= 400:
        raise AssertionError(f"HTTP {status}: {json.dumps(body)}")
    return body


def request_json_with_status(url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            body = error.read().decode("utf-8")
            return error.code, json.loads(body)
        finally:
            error.close()


def request_text_with_status(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        try:
            return error.code, error.read().decode("utf-8")
        finally:
            error.close()


if __name__ == "__main__":
    unittest.main()
