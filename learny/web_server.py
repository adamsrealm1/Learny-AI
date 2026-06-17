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
    SECOND_FALLBACK_GROQ_MODEL,
    THIRD_FALLBACK_GROQ_MODEL,
    GroqAnswerGenerator,
)
from .messages import GENERIC_ERROR_MESSAGE


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WASMER_ROOT = Path("/")
WASMER_APP_DIR = WASMER_ROOT / "app"
DEFAULT_STATIC_DIR = PROJECT_ROOT / "web"
DEFAULT_STATIC_ROOT = PROJECT_ROOT
ALLOWED_CORS_ORIGINS = {
    "https://learny.env.pm",
    "https://learny-ai-adamsrealm1.wasmer.app",
    "https://learny-ai.wasmer.app",
}


@dataclass(frozen=True)
class WebServerConfig:
    static_dir: Path
    generator_factory: Callable[[], AnswerGenerator | None]


class SessionStore:
    def __init__(self, max_turns: int = 8) -> None:
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
        server_version = "LearnyWeb/2.0"

        def do_GET(self) -> None:
            route = urlsplit(self.path).path
            if route == "/api/status":
                self._handle_status()
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
            groq_enabled = config.generator_factory() is not None
            self._send_json(
                {
                    "app": "Learny AI",
                    "ok": groq_enabled,
                    "groqEnabled": groq_enabled,
                    "primaryModel": PRIMARY_GROQ_MODEL,
                    "fallbackModel": FALLBACK_GROQ_MODEL,
                    "secondFallbackModel": SECOND_FALLBACK_GROQ_MODEL,
                    "thirdFallbackModel": THIRD_FALLBACK_GROQ_MODEL,
                    "models": list(DEFAULT_GROQ_MODELS),
                    "unknownMessage": DEFAULT_FALLBACK,
                    "error": None if groq_enabled else GENERIC_ERROR_MESSAGE,
                }
            )

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
            bot = Learny(
                generator=config.generator_factory(),
                history=history,
            )
            response = bot.reply(message)
            self._send_json(
                {
                    "sessionId": session_id,
                    "answer": response.answer,
                    "source": response.source,
                    "model": response.model,
                    "retryable": False,
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
                raise ValueError("Request body is invalid.") from error

            if not isinstance(body, dict):
                raise ValueError("Request body is invalid.")
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
    print(f"Groq models: {', '.join(DEFAULT_GROQ_MODELS)}")
    server.serve_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Learny AI as a Groq web server.")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--static", type=Path, default=_default_static_dir())
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = WebServerConfig(
        static_dir=args.static.resolve(),
        generator_factory=GroqAnswerGenerator.from_env,
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
