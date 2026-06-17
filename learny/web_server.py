from __future__ import annotations

import argparse
import json
import mimetypes
import os
import secrets
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlsplit

from .bot import DEFAULT_FALLBACK, AnswerGenerator, Learny
from .conversation import ConversationHistory
from .groq_client import (
    DEFAULT_GROQ_MODELS,
    FALLBACK_GROQ_MODEL,
    PRIMARY_GROQ_MODEL,
    GroqAnswerGenerator,
    is_unusable_generated_answer,
)
from .knowledge import KnowledgeFormatError, load_knowledge_file
from .messages import GENERIC_ERROR_MESSAGE


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WASMER_ROOT = Path("/")
WASMER_APP_DIR = WASMER_ROOT / "app"
WASMER_STATE_DIR = WASMER_ROOT / "state"
DEFAULT_STATIC_DIR = PROJECT_ROOT / "web"
DEFAULT_STATIC_ROOT = PROJECT_ROOT
LOCAL_STATE_DIR = PROJECT_ROOT / ".learny-state"
LOCAL_KNOWLEDGE_PATH = LOCAL_STATE_DIR / "knowledge.json"
WASMER_STATE_KNOWLEDGE_PATH = WASMER_STATE_DIR / "knowledge.json"
KNOWLEDGE_PATH_ENV = "LEARNY_KNOWLEDGE_PATH"
ALLOWED_CORS_ORIGINS = {
    "https://learny.env.pm",
    "https://learny-ai-adamsrealm1.wasmer.app",
    "https://learny-ai.wasmer.app",
}


@dataclass(frozen=True)
class WebServerConfig:
    static_dir: Path
    knowledge_path: Path
    generator_factory: Callable[[], AnswerGenerator | None]


class SessionStore:
    def __init__(self, max_turns: int = 6) -> None:
        self.max_turns = max_turns
        self._histories: dict[str, ConversationHistory] = {}

    def get(self, session_id: str | None) -> tuple[str, ConversationHistory]:
        clean_session_id = _clean_session_id(session_id)
        if clean_session_id is None:
            clean_session_id = secrets.token_urlsafe(18)

        history = self._histories.get(clean_session_id)
        if history is None:
            history = ConversationHistory(max_turns=self.max_turns)
            self._histories[clean_session_id] = history
        return clean_session_id, history


def create_handler(config: WebServerConfig) -> type[BaseHTTPRequestHandler]:
    session_store = SessionStore()

    class LearnyRequestHandler(BaseHTTPRequestHandler):
        server_version = "LearnyWeb/1.0"

        def do_GET(self) -> None:
            route = urlsplit(self.path).path
            if route == "/api/status":
                self._handle_status()
                return
            if route == "/api/knowledge":
                self._handle_knowledge()
                return
            self._serve_static(route)

        def do_POST(self) -> None:
            route = urlsplit(self.path).path
            if route == "/api/ask":
                self._handle_ask()
                return
            self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.NOT_FOUND)

        def do_OPTIONS(self) -> None:
            route = urlsplit(self.path).path
            if route.startswith("/api/"):
                self.send_response(HTTPStatus.NO_CONTENT)
                self._send_cors_headers()
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header(
                    "Access-Control-Allow-Headers",
                    "Content-Type, X-Learny-Session",
                )
                self.send_header("Access-Control-Max-Age", "86400")
                self.end_headers()
                return
            self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: Any) -> None:
            print(f"{self.address_string()} - {format % args}")

        def _handle_status(self) -> None:
            _repair_knowledge_file(config.knowledge_path)
            try:
                knowledge = load_knowledge_file(config.knowledge_path)
                knowledge_ok = True
                knowledge_count = len(knowledge.entries)
                knowledge_error = False
            except (FileNotFoundError, KnowledgeFormatError):
                knowledge_ok = False
                knowledge_count = 0
                knowledge_error = True

            self._send_json(
                {
                    "app": "Learny AI",
                    "ok": knowledge_ok,
                    "knowledgeCount": knowledge_count,
                    "knowledgePath": str(config.knowledge_path),
                    "groqEnabled": config.generator_factory() is not None,
                    "primaryModel": PRIMARY_GROQ_MODEL,
                    "fallbackModel": FALLBACK_GROQ_MODEL,
                    "models": list(DEFAULT_GROQ_MODELS),
                    "unknownMessage": DEFAULT_FALLBACK,
                    "error": GENERIC_ERROR_MESSAGE if knowledge_error else None,
                }
            )

        def _handle_knowledge(self) -> None:
            _repair_knowledge_file(config.knowledge_path)
            try:
                knowledge = load_knowledge_file(config.knowledge_path)
            except (FileNotFoundError, KnowledgeFormatError):
                self._send_json(
                    {"questions": [], "count": 0, "error": GENERIC_ERROR_MESSAGE},
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return

            questions = [
                {
                    "question": entry.question,
                    "answers": len(entry.answers),
                    "preview": entry.answers[0],
                }
                for entry in sorted(
                    knowledge.entries,
                    key=lambda entry: entry.question.casefold(),
                )
            ]
            self._send_json({"questions": questions, "count": len(questions)})

        def _handle_ask(self) -> None:
            try:
                body = self._read_json_body()
                message = _required_string(body, "message")
            except ValueError:
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.BAD_REQUEST)
                return

            session_id, history = session_store.get(
                _optional_string(body, "sessionId")
                or self.headers.get("X-Learny-Session")
            )
            _repair_knowledge_file(config.knowledge_path)
            try:
                bot = Learny.from_file(
                    config.knowledge_path,
                    generator=config.generator_factory(),
                    history=history,
                )
            except (FileNotFoundError, KnowledgeFormatError):
                self._send_json(
                    {"error": GENERIC_ERROR_MESSAGE},
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return

            response = bot.reply(message)
            self._send_json(
                {
                    "sessionId": session_id,
                    "answer": response.answer,
                    "source": response.source,
                    "learned": response.learned,
                    "matchedQuestion": response.matched_question,
                    "model": response.model,
                }
            )

        def _serve_static(self, route: str) -> None:
            if route in {"", "/"}:
                route = "/index.html"

            try:
                static_path = _safe_static_path(config.static_dir, route)
            except ValueError:
                self._send_text(GENERIC_ERROR_MESSAGE, HTTPStatus.NOT_FOUND)
                return

            if not static_path.is_file():
                self._send_text(GENERIC_ERROR_MESSAGE, HTTPStatus.NOT_FOUND)
                return

            content_type = mimetypes.guess_type(static_path.name)[0]
            if content_type is None:
                content_type = "application/octet-stream"

            payload = static_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            if static_path.suffix.lower() in {".css", ".js", ".png", ".jpg", ".webp"}:
                self.send_header("Cache-Control", "public, max-age=3600")
            else:
                self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def _read_json_body(self) -> dict[str, Any]:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                raise ValueError("Request body is required.")
            if content_length > 64_000:
                raise ValueError("Request body is too large.")

            raw_body = self.rfile.read(content_length).decode("utf-8")
            try:
                body = json.loads(raw_body)
            except json.JSONDecodeError as error:
                raise ValueError("Request body must be valid JSON.") from error

            if not isinstance(body, dict):
                raise ValueError("Request body must be a JSON object.")
            return body

        def _send_json(
            self,
            data: dict[str, Any],
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            payload = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(payload)

        def _send_text(
            self,
            text: str,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            payload = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(payload)

        def _send_cors_headers(self) -> None:
            origin = self.headers.get("Origin", "").strip()
            if not _is_allowed_cors_origin(origin):
                return
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    return LearnyRequestHandler


def run_server(
    host: str,
    port: int,
    config: WebServerConfig,
) -> None:
    handler = create_handler(config)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Learny web server running at http://{host}:{port}")
    print(f"Static files: {config.static_dir}")
    print(f"Knowledge file: {config.knowledge_path}")
    server.serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Learny AI as a web server.")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--static", type=Path, default=_default_static_dir())
    parser.add_argument("--knowledge", type=Path, default=_default_knowledge_path())
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Disable Groq learning even when GROQ_API_KEY is set.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    knowledge_path = args.knowledge.resolve()
    _ensure_knowledge_file(knowledge_path)
    _repair_knowledge_file(knowledge_path)
    generator_factory = (
        (lambda: None) if args.offline else GroqAnswerGenerator.from_env
    )
    config = WebServerConfig(
        static_dir=args.static.resolve(),
        knowledge_path=knowledge_path,
        generator_factory=generator_factory,
    )
    run_server(args.host, args.port, config)
    return 0


def _default_static_dir() -> Path:
    if (WASMER_APP_DIR / "index.html").exists():
        return WASMER_APP_DIR
    if (WASMER_ROOT / "index.html").exists():
        return WASMER_ROOT
    if (WASMER_ROOT / "web" / "index.html").exists():
        return WASMER_ROOT / "web"
    if (DEFAULT_STATIC_ROOT / "index.html").exists():
        return DEFAULT_STATIC_ROOT
    return DEFAULT_STATIC_DIR


def _default_knowledge_path() -> Path:
    env_path = os.environ.get(KNOWLEDGE_PATH_ENV, "").strip()
    if env_path:
        return Path(env_path)
    if WASMER_STATE_DIR.exists():
        return WASMER_STATE_KNOWLEDGE_PATH
    return LOCAL_KNOWLEDGE_PATH


def _ensure_knowledge_file(knowledge_path: Path) -> None:
    if knowledge_path.exists():
        return

    _write_json_file(knowledge_path, {"questions": {}})


def _repair_knowledge_file(knowledge_path: Path) -> None:
    raw_data, changed = _load_repairable_knowledge_json(knowledge_path)

    raw_questions = raw_data.get("questions")
    if isinstance(raw_questions, dict):
        changed = _repair_question_mapping(raw_questions) or changed
    elif isinstance(raw_questions, list):
        changed = _repair_question_list(raw_questions) or changed
    else:
        raw_data["questions"] = {}
        changed = True

    if changed:
        _write_json_file(knowledge_path, raw_data)


def _load_repairable_knowledge_json(knowledge_path: Path) -> tuple[dict[str, Any], bool]:
    raw_data = _read_strict_json_file(knowledge_path)
    if raw_data is not None:
        return raw_data, False

    raw_data = _read_recoverable_json_file(knowledge_path)
    if raw_data is not None:
        return raw_data, True

    for recovery_path in (_next_path(knowledge_path), _backup_path(knowledge_path)):
        raw_data = _read_strict_json_file(recovery_path)
        if raw_data is None:
            raw_data = _read_recoverable_json_file(recovery_path)
        if raw_data is None:
            continue
        return raw_data, True

    return {"questions": {}}, True


def _read_recoverable_json_file(path: Path) -> dict[str, Any] | None:
    try:
        raw_text = path.read_bytes().decode("utf-8", errors="ignore")
    except OSError:
        return None

    try:
        raw_data = json.loads(raw_text)
    except json.JSONDecodeError:
        raw_data = _parse_recoverable_json_prefix(raw_text)

    return raw_data if isinstance(raw_data, dict) else None


def _read_strict_json_file(path: Path) -> dict[str, Any] | None:
    try:
        raw_text = path.read_text(encoding="utf-8")
        raw_data = json.loads(raw_text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return raw_data if isinstance(raw_data, dict) else None


def _parse_recoverable_json_prefix(raw_text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    try:
        parsed, _ = decoder.raw_decode(raw_text.lstrip())
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _repair_question_mapping(raw_questions: dict[Any, Any]) -> bool:
    changed = False
    for question, raw_answers in list(raw_questions.items()):
        if not isinstance(question, str):
            continue
        repaired_answers = _repaired_answers(question, raw_answers)
        if repaired_answers is None:
            continue
        if not repaired_answers:
            del raw_questions[question]
            changed = True
        elif repaired_answers != raw_answers:
            raw_questions[question] = repaired_answers
            changed = True
    return changed


def _repair_question_list(raw_questions: list[Any]) -> bool:
    changed = False
    for entry in list(raw_questions):
        if not isinstance(entry, dict):
            continue
        question = entry.get("question")
        if not isinstance(question, str):
            continue
        repaired_answers = _repaired_answers(question, entry.get("answers"))
        if repaired_answers is None:
            continue
        if not repaired_answers:
            raw_questions.remove(entry)
            changed = True
        elif repaired_answers != entry.get("answers"):
            entry["answers"] = repaired_answers
            changed = True
    return changed


def _repaired_answers(question: str, raw_answers: Any) -> list[str] | None:
    if isinstance(raw_answers, str):
        answers = [raw_answers]
    elif isinstance(raw_answers, list):
        answers = [answer for answer in raw_answers if isinstance(answer, str)]
    else:
        return None
    return [
        answer
        for answer in answers
        if not is_unusable_generated_answer(question, answer)
    ]


def _write_json_file(path: Path, raw_data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_and_verify_json(_next_path(path), raw_data)
    _write_and_verify_json(_backup_path(path), raw_data)
    _write_and_verify_json(path, raw_data)


def _write_and_verify_json(path: Path, raw_data: dict[str, Any]) -> None:
    payload = (json.dumps(raw_data, indent=2) + "\n").encode("utf-8")
    try:
        path.unlink()
    except FileNotFoundError:
        pass

    open_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, open_flags, 0o666)
    try:
        view = memoryview(payload)
        bytes_written = 0
        while bytes_written < len(payload):
            bytes_written += os.write(descriptor, view[bytes_written:])
        try:
            os.fsync(descriptor)
        except OSError:
            pass
    finally:
        os.close(descriptor)

    if _read_strict_json_file(path) != raw_data:
        raise KnowledgeFormatError(f"{path} could not be verified after writing.")


def _next_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.next")


def _backup_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.backup")


def _safe_static_path(static_dir: Path, route: str) -> Path:
    route = unquote(route).replace("\\", "/").lstrip("/")
    if not route:
        route = "index.html"
    if _uses_root_static_layout(static_dir) and route != "index.html" and not route.startswith("web/"):
        raise ValueError("Static path is not part of the public web files.")
    candidate = (static_dir / route).resolve()
    static_root = static_dir.resolve()
    if candidate == static_root or static_root not in candidate.parents:
        raise ValueError("Static path escaped the web directory.")
    return candidate


def _uses_root_static_layout(static_dir: Path) -> bool:
    return (static_dir / "index.html").is_file() and (static_dir / "web").is_dir()


def _is_allowed_cors_origin(origin: str) -> bool:
    if origin in ALLOWED_CORS_ORIGINS:
        return True
    return origin.startswith("http://127.0.0.1:") or origin.startswith("http://localhost:")


def _required_string(body: dict[str, Any], key: str) -> str:
    value = body.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key!r} must be a non-empty string.")
    return value.strip()


def _optional_string(body: dict[str, Any], key: str) -> str | None:
    value = body.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _clean_session_id(session_id: str | None) -> str | None:
    if session_id is None:
        return None
    session_id = session_id.strip()
    if not session_id:
        return None
    return "".join(character for character in session_id if character.isalnum() or character in "-_")[:80]
