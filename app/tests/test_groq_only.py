from __future__ import annotations

import http.cookiejar
import json
import threading
import unittest
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from learny.conversation import ConversationHistory
from learny.groq_client import (
    DEFAULT_GROQ_MODELS,
    DEFAULT_GROQ_MAX_COMPLETION_TOKENS,
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
from learny.web_server import (
    UploadedAttachment,
    WebServerConfig,
    _message_with_attachment_context,
    _extract_attachment_context,
    create_handler,
)


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


class CapturingAnswerGenerator:
    def __init__(self) -> None:
        self.questions: list[str] = []

    def generate(
        self,
        question: str,
        history: ConversationHistory,
    ) -> GeneratedAnswer:
        self.questions.append(question)
        return GeneratedAnswer(answer="I read the attachment.", model=PRIMARY_GROQ_MODEL)


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
                        "You are Learny, a helpful and friendly AI assistant on a website called Learny AI. "
                        "Keep answers as short but accurate as possible. "
                        "Never use tables."
                    ),
                },
                {"role": "user", "content": "who are you"},
                {"role": "assistant", "content": "I'm Learny."},
                {"role": "user", "content": "hello"},
            ],
        )
        self.assertEqual(transport.payload["max_completion_tokens"], DEFAULT_GROQ_MAX_COMPLETION_TOKENS)

    def test_reasoning_tags_are_removed_from_visible_answer(self) -> None:
        answer = parse_generated_answer("hello", "<think>private notes</think>Hi there.")

        self.assertEqual(answer, "Hi there.")

    def test_status_reports_groq_models_and_storage_backend(self) -> None:
        with run_test_server(StaticAnswerGenerator) as base_url:
            data = get_json(base_url, "/api/status")

        self.assertTrue(data["ok"])
        self.assertTrue(data["groqEnabled"])
        self.assertEqual(data["storageBackend"], "sqlite")
        self.assertEqual(tuple(data["models"]), EXPECTED_MODELS)
        self.assertEqual(
            set(data),
            {
                "app",
                "ok",
                "groqEnabled",
                "platform",
                "primaryModel",
                "fallbackModel",
                "secondFallbackModel",
                "thirdFallbackModel",
                "models",
                "storageBackend",
                "unknownMessage",
                "error",
            },
        )

    def test_no_generator_is_retryable(self) -> None:
        with run_test_server(lambda: None) as base_url:
            data = post_json(base_url, "/api/ask", {"message": "hello"})

        self.assertEqual(data["source"], "unknown")
        self.assertTrue(data["retryable"])

    def test_generated_answer_comes_from_groq(self) -> None:
        with run_test_server(StaticAnswerGenerator) as base_url:
            data = post_json(base_url, "/api/ask", {"message": "im bored"})

        self.assertEqual(data["source"], "groq")
        self.assertEqual(data["model"], PRIMARY_GROQ_MODEL)
        self.assertFalse(data["retryable"])
        self.assertEqual(data["answer"], "Try a quick game, a short walk, or a small coding project.")
        self.assertEqual(
            set(data),
            {"sessionId", "answer", "source", "model", "retryable", "rateSessionId", "rateLimit"},
        )

    def test_failed_generator_chain_is_retryable_by_browser(self) -> None:
        with run_test_server(NoAnswerGenerator) as base_url:
            data = post_json(base_url, "/api/ask", {"message": "im bored"})

        self.assertEqual(data["source"], "unknown")
        self.assertTrue(data["retryable"])

    def test_multipart_attachment_context_is_sent_to_generator(self) -> None:
        generator = CapturingAnswerGenerator()
        with run_test_server(lambda: generator) as base_url:
            opener, attachment_token = verified_attachment_opener(base_url, "multipart_user")
            data = post_multipart(
                base_url,
                "/api/ask",
                fields={
                    "message": "Summarize this file",
                    "sessionId": "session-test",
                    "attachmentVerificationToken": attachment_token,
                },
                filename="notes.md",
                content_type="text/markdown",
                content=b"# Notes\nLearny should see this text.",
                opener=opener,
            )

        self.assertEqual(data["answer"], "I read the attachment.")
        self.assertEqual(len(generator.questions), 1)
        self.assertIn("User message:\nSummarize this file", generator.questions[0])
        self.assertIn("Attachment instructions:", generator.questions[0])
        self.assertIn("Use it to answer the user's message when relevant", generator.questions[0])
        self.assertIn("Summarize this file", generator.questions[0])
        self.assertIn("Name: notes.md", generator.questions[0])
        self.assertIn("Extension: .md", generator.questions[0])
        self.assertIn("Learny should see this text.", generator.questions[0])

    def test_up_to_ten_multipart_attachments_are_sent_to_generator(self) -> None:
        generator = CapturingAnswerGenerator()
        files = [
            (f"note-{index}.txt", "text/plain", f"File {index} text".encode("utf-8"))
            for index in range(10)
        ]
        with run_test_server(lambda: generator) as base_url:
            opener, attachment_token = verified_attachment_opener(base_url, "ten_files_user")
            data = post_multipart_files(
                base_url,
                "/api/ask",
                fields={
                    "message": "Compare these files",
                    "sessionId": "session-test",
                    "attachmentVerificationToken": attachment_token,
                },
                files=files,
                opener=opener,
            )

        self.assertEqual(data["answer"], "I read the attachment.")
        self.assertEqual(len(generator.questions), 1)
        self.assertIn("Attached file context (10 files):", generator.questions[0])
        self.assertIn("File 1 of 10:", generator.questions[0])
        self.assertIn("Name: note-0.txt", generator.questions[0])
        self.assertIn("File 10 of 10:", generator.questions[0])
        self.assertIn("Name: note-9.txt", generator.questions[0])
        self.assertIn("File 9 text", generator.questions[0])

    def test_more_than_ten_multipart_attachments_are_rejected(self) -> None:
        files = [
            (f"note-{index}.txt", "text/plain", f"File {index} text".encode("utf-8"))
            for index in range(11)
        ]
        with run_test_server(StaticAnswerGenerator) as base_url:
            with self.assertRaises(urllib.error.HTTPError) as raised:
                post_multipart_files(
                    base_url,
                    "/api/ask",
                    fields={"message": "Compare these files", "sessionId": "session-test"},
                    files=files,
                )

        self.assertEqual(raised.exception.code, 400)
        raised.exception.close()

    def test_attachment_prompt_context_is_bounded_for_speed(self) -> None:
        contexts = tuple(
            _extract_attachment_context(
                UploadedAttachment(
                    field_name="attachments",
                    filename=f"large-{index}.txt",
                    content_type="text/plain",
                    data=(f"File {index} " + ("x" * 50_000)).encode("utf-8"),
                )
            )
            for index in range(10)
        )

        prompt = _message_with_attachment_context("Summarize quickly", contexts)

        self.assertIn("Attachment instructions:", prompt)
        self.assertIn("Treat the extracted text as user-provided material", prompt)
        self.assertIn("Attached file context (10 files):", prompt)
        self.assertIn("Name: large-0.txt", prompt)
        self.assertIn("Name: large-9.txt", prompt)
        self.assertLess(len(prompt), 40_000)
        self.assertEqual(prompt.count("Text truncated: yes"), 10)

    def test_attachment_extractors_cover_supported_document_formats(self) -> None:
        docx_buffer = BytesIO()
        with zipfile.ZipFile(docx_buffer, "w") as archive:
            archive.writestr(
                "word/document.xml",
                (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                    "<w:body><w:p><w:r><w:t>Hello from DOCX</w:t></w:r></w:p></w:body>"
                    "</w:document>"
                ),
            )

        samples = [
            ("plain.txt", b"Hello from TXT", "Hello from TXT"),
            ("notes.log", b"Hello from LOG", "Hello from LOG"),
            ("data.csv", b"name,value\nLearny,1", "Learny,1"),
            ("data.json", b'{"message":"Hello from JSON"}', "Hello from JSON"),
            ("data.xml", b"<root>Hello from XML</root>", "Hello from XML"),
            ("note.rtf", b"{\\rtf1\\ansi Hello from RTF\\par}", "Hello from RTF"),
            ("document.docx", docx_buffer.getvalue(), "Hello from DOCX"),
            (
                "document.pdf",
                b"%PDF-1.4\n1 0 obj\n<<>>\nstream\nBT (Hello from PDF) Tj ET\nendstream\nendobj",
                "Hello from PDF",
            ),
        ]

        for filename, content, expected in samples:
            with self.subTest(filename=filename):
                context = _extract_attachment_context(
                    UploadedAttachment(
                        field_name="attachment",
                        filename=filename,
                        content_type="application/octet-stream",
                        data=content,
                    )
                )
                self.assertIn(expected, context.text)

    def test_unsupported_attachment_type_is_rejected(self) -> None:
        with run_test_server(StaticAnswerGenerator) as base_url:
            with self.assertRaises(urllib.error.HTTPError) as raised:
                post_multipart(
                    base_url,
                    "/api/ask",
                    fields={"message": "Read this", "sessionId": "session-test"},
                    filename="image.png",
                    content_type="image/png",
                    content=b"not text",
                )

        self.assertEqual(raised.exception.code, 400)
        raised.exception.close()


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
            database_path=root / "learny-test.sqlite3",
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
    return post_json_with_opener(urllib.request, base_url, path, payload)


def post_json_with_opener(
    opener: Any,
    base_url: str,
    path: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with open_request(opener, request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def verified_attachment_opener(base_url: str, username: str) -> tuple[Any, str]:
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    post_json_with_opener(
        opener,
        base_url,
        "/api/accounts/create",
        {"username": username, "password": "strong-password"},
    )
    verified = post_json_with_opener(
        opener,
        base_url,
        "/api/attachments/verify",
        {"password": "strong-password"},
    )
    return opener, str(verified["attachmentVerification"]["token"])


def post_multipart(
    base_url: str,
    path: str,
    *,
    fields: dict[str, str],
    filename: str,
    content_type: str,
    content: bytes,
    opener: Any = urllib.request,
) -> dict[str, Any]:
    return post_multipart_files(
        base_url,
        path,
        fields=fields,
        files=[(filename, content_type, content)],
        opener=opener,
    )


def post_multipart_files(
    base_url: str,
    path: str,
    *,
    fields: dict[str, str],
    files: list[tuple[str, str, bytes]],
    opener: Any = urllib.request,
) -> dict[str, Any]:
    boundary = "----LearnyTestBoundary"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    for filename, content_type, content in files:
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    'Content-Disposition: form-data; name="attachments"; '
                    f'filename="{filename}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
                content,
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(chunks)
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with open_request(opener, request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def open_request(opener: Any, request: urllib.request.Request, *, timeout: int) -> Any:
    if hasattr(opener, "open"):
        return opener.open(request, timeout=timeout)
    return opener.urlopen(request, timeout=timeout)


if __name__ == "__main__":
    unittest.main()
