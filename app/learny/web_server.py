from __future__ import annotations

import argparse
import base64
import binascii
import html
import io
import json
import mimetypes
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.request
import zipfile
import zlib
from dataclasses import dataclass
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode, unquote, urlsplit
from xml.etree import ElementTree

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
from .database import (
    DEFAULT_ADMIN_USERNAME,
    DEFAULT_RATE_LIMIT_TIME_ZONE,
    AccountError,
    AuthenticationError,
    RATE_LIMIT_LIMIT,
    RATE_LIMIT_WINDOW_MS,
)
from .messages import GENERIC_ERROR_MESSAGE
from .storage import create_learny_database


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPOSITORY_ROOT = PROJECT_ROOT.parent
WASMER_ROOT = Path("/")
WASMER_SITE_DIR = WASMER_ROOT / "site"
WASMER_APP_DIR = WASMER_ROOT / "app"
DEFAULT_STATIC_DIR = PROJECT_ROOT / "web"
DEFAULT_STATIC_ROOT = PROJECT_ROOT
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
ACCOUNT_SESSION_COOKIE = "learny_account"
PUBLIC_ROOT_FILES = {
    "index.html",
}
ALLOWED_CORS_ORIGINS = {
    "https://learny.env.pm",
    "https://learny-ai.wasmer.app",
    "https://learny-ai-adamsrealm1.wasmer.app",
}
PROFILE_PICTURE_MAX_BYTES = 512 * 1024
PROFILE_PICTURE_MAX_BODY_BYTES = 800_000
PROFILE_PICTURE_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/webp;base64,",
    "data:image/gif;base64,",
)
ASK_JSON_MAX_BYTES = 64_000
ATTACHMENT_LIMIT = 5
ATTACHMENT_MAX_BYTES = 4 * 1024 * 1024
ASK_MULTIPART_MAX_BYTES = (ATTACHMENT_LIMIT * ATTACHMENT_MAX_BYTES) + 512_000
ATTACHMENT_TEXT_MAX_CHARS = 24_000
ATTACHMENT_PROMPT_TOTAL_CHARS = 32_000
ATTACHMENT_PROMPT_MIN_CHARS = 1_500
ATTACHMENT_VERIFICATION_TTL_MS = 15 * 60 * 1000
RECAPTCHA_VERIFY_URL = "https://www.google.com/recaptcha/api/siteverify"
SUPPORTED_ATTACHMENT_EXTENSIONS = {
    "txt",
    "md",
    "log",
    "docx",
    "rtf",
    "pdf",
    "csv",
    "json",
    "xml",
}
PLAIN_TEXT_ATTACHMENT_EXTENSIONS = {"txt", "md", "log", "csv", "json", "xml"}
GUEST_RATE_LIMIT_LIMIT = 30


@dataclass(frozen=True)
class WebServerConfig:
    static_dir: Path
    generator_factory: Callable[[], AnswerGenerator | None]
    database_path: Path | None = None
    captcha_site_key: str = ""
    captcha_secret_key: str = ""
    captcha_verifier: Callable[[str, str | None], bool] | None = None


@dataclass(frozen=True)
class UploadedAttachment:
    field_name: str
    filename: str
    content_type: str
    data: bytes


@dataclass(frozen=True)
class AttachmentContext:
    filename: str
    extension: str
    content_type: str
    size: int
    text: str
    truncated: bool


class CaptchaService:
    def __init__(
        self,
        *,
        site_key: str = "",
        secret_key: str = "",
        verifier: Callable[[str, str | None], bool] | None = None,
    ) -> None:
        self.site_key = site_key.strip()
        self.secret_key = secret_key.strip()
        self._verifier = verifier

    @property
    def enabled(self) -> bool:
        return bool(self.site_key and (self.secret_key or self._verifier))

    def public_config(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "siteKey": self.site_key if self.enabled else "",
        }

    def verify(self, token: str | None, remote_ip: str | None = None) -> bool:
        if not self.enabled:
            return True
        clean_token = str(token or "").strip()
        if not clean_token:
            return False
        if self._verifier is not None:
            try:
                return bool(self._verifier(clean_token, remote_ip))
            except Exception:
                return False
        return _verify_google_recaptcha(self.secret_key, clean_token, remote_ip)


class AttachmentVerificationStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tokens: dict[str, tuple[int, int]] = {}

    def create(self, account_id: int) -> dict[str, Any]:
        self._prune()
        token = secrets.token_urlsafe(32)
        expires_at = _now_ms() + ATTACHMENT_VERIFICATION_TTL_MS
        with self._lock:
            self._tokens[token] = (account_id, expires_at)
        return {"token": token, "expiresAt": expires_at}

    def verify(self, account_id: int, token: str | None) -> bool:
        clean_token = str(token or "").strip()
        if not clean_token:
            return False
        now = _now_ms()
        with self._lock:
            record = self._tokens.get(clean_token)
            if record is None:
                return False
            stored_account_id, expires_at = record
            if expires_at <= now:
                self._tokens.pop(clean_token, None)
                return False
            return stored_account_id == account_id

    def _prune(self) -> None:
        now = _now_ms()
        with self._lock:
            expired_tokens = [
                token for token, (_, expires_at) in self._tokens.items() if expires_at <= now
            ]
            for token in expired_tokens:
                self._tokens.pop(token, None)


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
    database = create_learny_database(
        config.database_path or _default_database_path(),
        prefer_wasmer_database=config.database_path is None,
    )
    captcha = CaptchaService(
        site_key=config.captcha_site_key,
        secret_key=config.captcha_secret_key,
        verifier=config.captcha_verifier,
    )
    attachment_verifications = AttachmentVerificationStore()

    class LearnyRequestHandler(BaseHTTPRequestHandler):
        server_version = "LearnyWeb/2.0"

        def do_GET(self) -> None:
            route = urlsplit(self.path).path
            if route == "/api/status":
                self._handle_status()
                return
            if route == "/api/account":
                self._handle_account()
                return
            if route == "/api/rate-limit":
                self._handle_rate_limit()
                return
            if route == "/api/platform":
                self._handle_platform()
                return
            if route == "/api/captcha/config":
                self._handle_captcha_config()
                return
            if route == "/api/admin/portal":
                self._handle_admin_portal()
                return
            if route == "/api/chats":
                self._handle_get_chats()
                return
            self._serve_static(route)

        def do_POST(self) -> None:
            route = urlsplit(self.path).path
            if route == "/api/ask":
                self._handle_ask()
                return
            if route == "/api/accounts/create":
                self._handle_create_account()
                return
            if route == "/api/accounts/sign-in":
                self._handle_sign_in()
                return
            if route == "/api/accounts/sign-out":
                self._handle_sign_out()
                return
            if route == "/api/accounts/delete":
                self._handle_delete_account()
                return
            if route == "/api/account/profile-picture":
                self._handle_profile_picture()
                return
            if route == "/api/attachments/verify":
                self._handle_attachment_verification()
                return
            if route == "/api/rate-limits/reset":
                self._handle_reset_rate_limits()
                return
            if route == "/api/admin/platform":
                self._handle_admin_platform()
                return
            if route == "/api/admin/rate-limit/reset":
                self._handle_admin_reset_rate_limit()
                return
            if route == "/api/admin/ban":
                self._handle_admin_ban()
                return
            if route == "/api/admin/unban":
                self._handle_admin_unban()
                return
            if route == "/api/admin/delete-account":
                self._handle_admin_delete_account()
                return
            if route == "/api/admin/role":
                self._handle_admin_role()
                return
            if route == "/api/chats/sync":
                self._handle_sync_chats()
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
                    "Content-Type, X-Learny-Session, X-Learny-Rate-Session, X-Learny-Time-Zone",
                )
                self.send_header("Access-Control-Max-Age", "86400")
                self.end_headers()
                return
            self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: Any) -> None:
            print(f"{self.address_string()} - {format % args}")

        def _handle_status(self) -> None:
            groq_enabled = config.generator_factory() is not None
            platform = database.platform_state()
            self._send_json(
                {
                    "app": "Learny AI",
                    "ok": groq_enabled and bool(platform["available"]),
                    "groqEnabled": groq_enabled,
                    "platform": _public_platform(platform),
                    "primaryModel": PRIMARY_GROQ_MODEL,
                    "fallbackModel": FALLBACK_GROQ_MODEL,
                    "secondFallbackModel": SECOND_FALLBACK_GROQ_MODEL,
                    "thirdFallbackModel": THIRD_FALLBACK_GROQ_MODEL,
                    "models": list(DEFAULT_GROQ_MODELS),
                    "storageBackend": getattr(database, "backend_name", "unknown"),
                    "unknownMessage": DEFAULT_FALLBACK,
                    "error": None if groq_enabled else GENERIC_ERROR_MESSAGE,
                }
            )

        def _handle_account(self) -> None:
            account = self._current_account()
            platform = database.platform_state()
            ban = self._current_ban(account)
            if account is None:
                self._send_json(
                    {
                        "authenticated": False,
                        "account": None,
                        "stats": None,
                        "platform": _public_platform(platform),
                        "ban": _public_ban_from_database(ban, database) if ban else None,
                    },
                    HTTPStatus.FORBIDDEN if ban else HTTPStatus.OK,
                )
                return

            self._send_json(
                {
                    "authenticated": True,
                    "account": _public_account(account),
                    "stats": database.account_stats(int(account["id"])),
                    "platform": _public_platform(platform),
                    "ban": _public_ban_from_database(ban, database) if ban else None,
                }
            )

        def _handle_platform(self) -> None:
            account = self._current_account()
            platform = database.platform_state()
            ban = self._current_ban(account)
            self._send_json(
                {
                    "platform": _public_platform(platform),
                    "ban": _public_ban_from_database(ban, database) if ban else None,
                    "account": _public_account(account) if account else None,
                },
                HTTPStatus.FORBIDDEN if ban else HTTPStatus.OK,
            )

        def _handle_captcha_config(self) -> None:
            self._send_json({"captcha": captcha.public_config()})

        def _handle_admin_portal(self) -> None:
            admin = self._require_admin_account()
            if admin is None:
                return
            self._send_json(
                _admin_portal_payload(
                    database,
                    self._rate_limit_time_zone(),
                )
            )

        def _handle_create_account(self) -> None:
            try:
                body = self._read_json_body()
                username = _required_string(body, "username")
                email = _required_string(body, "email")
                password = _required_string(body, "password")
                if not self._verify_captcha_from_body(body):
                    self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.FORBIDDEN)
                    return
                ban = self._ban_for(username=username)
                if ban:
                    self._send_ban_response(ban)
                    return
                account = database.create_account(username, password, email)
                token = database.create_session(int(account["id"]))
            except (ValueError, AccountError):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.BAD_REQUEST)
                return

            self._send_json(
                {
                    "authenticated": True,
                    "account": _public_account(account),
                    "stats": database.account_stats(int(account["id"])),
                    "platform": _public_platform(database.platform_state()),
                    "ban": None,
                },
                extra_headers=[_account_cookie_header(token, self._needs_cross_site_cookie())],
            )

        def _handle_sign_in(self) -> None:
            try:
                body = self._read_json_body()
                username = _required_string(body, "username")
                email = _optional_string(body, "email")
                password = _required_string(body, "password")
                if not self._verify_captcha_from_body(body):
                    self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.FORBIDDEN)
                    return
                ban = self._ban_for(username=username)
                if ban:
                    self._send_ban_response(ban)
                    return
                account = database.authenticate(username, password, email)
                ban = self._ban_for(username=str(account["username"]))
                if ban:
                    self._send_ban_response(ban)
                    return
                token = database.create_session(int(account["id"]))
            except AuthenticationError as error:
                self._send_json(
                    {"error": str(error), "authErrorFields": list(error.fields)},
                    HTTPStatus.UNAUTHORIZED,
                )
                return
            except (ValueError, AccountError):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.UNAUTHORIZED)
                return

            self._send_json(
                {
                    "authenticated": True,
                    "account": _public_account(account),
                    "stats": database.account_stats(int(account["id"])),
                    "platform": _public_platform(database.platform_state()),
                    "ban": None,
                },
                extra_headers=[_account_cookie_header(token, self._needs_cross_site_cookie())],
            )

        def _handle_sign_out(self) -> None:
            database.delete_session(self._account_session_token())
            self._send_json(
                {"authenticated": False, "account": None, "stats": None},
                extra_headers=[_clear_account_cookie_header(self._needs_cross_site_cookie())],
            )

        def _handle_delete_account(self) -> None:
            account = self._current_account()
            if account is None:
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.UNAUTHORIZED)
                return
            try:
                body = self._read_json_body()
            except ValueError:
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.BAD_REQUEST)
                return
            if not self._verify_captcha_from_body(body):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.FORBIDDEN)
                return

            database.delete_account(int(account["id"]))
            self._send_json(
                {"deleted": True, "authenticated": False, "account": None, "stats": None},
                extra_headers=[_clear_account_cookie_header(self._needs_cross_site_cookie())],
            )

        def _handle_attachment_verification(self) -> None:
            account = self._current_account()
            if account is None:
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.UNAUTHORIZED)
                return
            ban = self._current_ban(account)
            if ban:
                self._send_ban_response(ban)
                return
            try:
                body = self._read_json_body()
                password = _required_string(body, "password")
            except ValueError:
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.BAD_REQUEST)
                return
            if not self._verify_captcha_from_body(body):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.FORBIDDEN)
                return
            if not database.verify_password(int(account["id"]), password):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.UNAUTHORIZED)
                return

            updated_account = database.mark_attachments_verified(int(account["id"]))
            verification = attachment_verifications.create(int(account["id"]))
            self._send_json(
                {
                    "ok": True,
                    "authenticated": True,
                    "account": _public_account(updated_account),
                    "stats": database.account_stats(int(account["id"])),
                    "attachmentVerification": {
                        "token": verification["token"],
                        "expiresAt": verification["expiresAt"],
                        "verified": True,
                    },
                }
            )

        def _handle_profile_picture(self) -> None:
            account = self._current_account()
            if account is None:
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.UNAUTHORIZED)
                return

            try:
                body = self._read_json_body(max_bytes=PROFILE_PICTURE_MAX_BODY_BYTES)
                profile_picture = _clean_profile_picture(body.get("profilePicture"))
                updated_account = database.update_profile_picture(int(account["id"]), profile_picture)
            except (ValueError, AccountError):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.BAD_REQUEST)
                return

            self._send_json(
                {
                    "authenticated": True,
                    "account": _public_account(updated_account),
                    "stats": database.account_stats(int(account["id"])),
                }
            )

        def _handle_reset_rate_limits(self) -> None:
            account = self._current_account()
            if account is None:
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.UNAUTHORIZED)
                return
            if not _is_admin_account(account):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.FORBIDDEN)
                return

            deleted = database.clear_rate_limits()
            rate_session_id = _rate_session_id(self.headers.get("X-Learny-Rate-Session"))
            time_zone = self._rate_limit_time_zone()
            rate_limit_identity, rate_limit_size = _rate_limit_policy(account, rate_session_id)
            rate_limit = database.peek_rate_limit(
                rate_limit_identity,
                limit=rate_limit_size,
                window_ms=RATE_LIMIT_WINDOW_MS,
                time_zone=time_zone,
            )
            self._send_json(
                {
                    "ok": True,
                    "deleted": deleted,
                    "rateSessionId": rate_session_id,
                    "rateLimit": _public_rate_limit(rate_limit),
                }
            )

        def _handle_rate_limit(self) -> None:
            account = self._current_account()
            ban = self._current_ban(account)
            if ban:
                self._send_ban_response(ban)
                return
            rate_session_id = _rate_session_id(self.headers.get("X-Learny-Rate-Session"))
            time_zone = self._rate_limit_time_zone()
            rate_limit_identity, rate_limit_size = _rate_limit_policy(account, rate_session_id)
            rate_limit = database.peek_rate_limit(
                rate_limit_identity,
                limit=rate_limit_size,
                window_ms=RATE_LIMIT_WINDOW_MS,
                time_zone=time_zone,
            )
            self._send_json(
                {
                    "rateSessionId": rate_session_id,
                    "rateLimit": _public_rate_limit(rate_limit),
                }
            )

        def _handle_admin_platform(self) -> None:
            admin = self._require_admin_account()
            if admin is None:
                return
            try:
                body = self._read_json_body()
                available = bool(body.get("available"))
                database.set_platform_available(available)
            except (ValueError, AccountError):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json(
                _admin_portal_payload(
                    database,
                    self._rate_limit_time_zone(),
                )
            )

        def _handle_admin_reset_rate_limit(self) -> None:
            admin = self._require_admin_account()
            if admin is None:
                return
            try:
                body = self._read_json_body()
                username = _required_string(body, "username")
                target_account = _account_by_username(database, username)
                if target_account is None:
                    raise AccountError("Account could not be found.")
                time_zone = self._rate_limit_time_zone()
                rate_limit_identity, rate_limit_size = _rate_limit_policy(target_account)
                deleted = database.clear_rate_limit(rate_limit_identity)
                rate_limit = database.peek_rate_limit(
                    rate_limit_identity,
                    limit=rate_limit_size,
                    window_ms=RATE_LIMIT_WINDOW_MS,
                    time_zone=time_zone,
                )
            except (ValueError, AccountError):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json(
                {
                    **_admin_portal_payload(database, time_zone),
                    "deleted": deleted,
                    "rateLimit": _public_rate_limit(rate_limit),
                    "resetRateLimit": _public_rate_limit(rate_limit),
                }
            )

        def _handle_admin_ban(self) -> None:
            admin = self._require_admin_account()
            if admin is None:
                return
            try:
                body = self._read_json_body()
                database.ban_identity(
                    _required_string(body, "kind"),
                    _required_string(body, "target"),
                    _optional_string(body, "reason") or "",
                    created_by=str(admin["username"]),
                )
            except (ValueError, AccountError):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json(
                _admin_portal_payload(
                    database,
                    self._rate_limit_time_zone(),
                )
            )

        def _handle_admin_unban(self) -> None:
            admin = self._require_admin_account()
            if admin is None:
                return
            try:
                body = self._read_json_body()
                database.unban_identity(
                    _required_string(body, "kind"),
                    _required_string(body, "target"),
                )
            except (ValueError, AccountError):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json(
                _admin_portal_payload(
                    database,
                    self._rate_limit_time_zone(),
                )
            )

        def _handle_admin_delete_account(self) -> None:
            admin = self._require_admin_account()
            if admin is None:
                return
            try:
                body = self._read_json_body()
                deleted = database.delete_account_by_username(_required_string(body, "username"))
            except (ValueError, AccountError):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json(
                {
                    **_admin_portal_payload(
                        database,
                        self._rate_limit_time_zone(),
                    ),
                    "deleted": deleted,
                }
            )

        def _handle_admin_role(self) -> None:
            admin = self._require_admin_account()
            if admin is None:
                return
            if not _is_owner_admin_account(admin):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.FORBIDDEN)
                return
            try:
                body = self._read_json_body()
                updated = database.set_account_admin(
                    _required_string(body, "username"),
                    bool(body.get("admin")),
                )
            except (ValueError, AccountError):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json(
                {
                    **_admin_portal_payload(
                        database,
                        self._rate_limit_time_zone(),
                    ),
                    "updatedAccount": _public_account(updated),
                }
            )

        def _handle_get_chats(self) -> None:
            account = self._current_account()
            if account is None:
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.UNAUTHORIZED)
                return
            ban = self._current_ban(account)
            if ban:
                self._send_ban_response(ban)
                return

            self._send_json({"chats": database.list_chats(int(account["id"]))})

        def _handle_sync_chats(self) -> None:
            account = self._current_account()
            if account is None:
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.UNAUTHORIZED)
                return
            ban = self._current_ban(account)
            if ban:
                self._send_ban_response(ban)
                return

            try:
                body = self._read_json_body()
                chats = body.get("chats", [])
                if not isinstance(chats, list):
                    raise ValueError("chats must be a list.")
                stored_chats = database.replace_account_chats(int(account["id"]), chats)
            except ValueError:
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.BAD_REQUEST)
                return

            self._send_json({"chats": stored_chats, "stats": database.account_stats(int(account["id"]))})

        def _handle_ask(self) -> None:
            try:
                body = self._read_ask_body()
                message = _required_string(body, "message")
                attachment_contexts = _attachment_contexts_from_body(body)
            except ValueError:
                self._send_json(
                    {"error": GENERIC_ERROR_MESSAGE, "retryable": False},
                    HTTPStatus.BAD_REQUEST,
                )
                return

            account = self._current_account()
            ban = self._current_ban(account)
            if ban:
                self._send_ban_response(ban)
                return
            if attachment_contexts:
                if account is None:
                    self._send_json(
                        {"error": GENERIC_ERROR_MESSAGE, "retryable": False},
                        HTTPStatus.UNAUTHORIZED,
                    )
                    return
                account_id = int(account["id"])
                if not database.attachments_verified(account_id):
                    verification_token = _optional_string(body, "attachmentVerificationToken")
                    if not attachment_verifications.verify(account_id, verification_token):
                        self._send_json(
                            {"error": GENERIC_ERROR_MESSAGE, "retryable": False},
                            HTTPStatus.FORBIDDEN,
                        )
                        return
                    database.mark_attachments_verified(account_id)
            platform = database.platform_state()
            if not platform.get("available", True):
                self._send_json(
                    {
                        "error": GENERIC_ERROR_MESSAGE,
                        "retryable": False,
                        "platform": _public_platform(platform),
                    },
                    HTTPStatus.SERVICE_UNAVAILABLE,
                )
                return
            chat_id = _optional_string(body, "chatId")
            requested_session_id = (
                _optional_string(body, "sessionId")
                or self.headers.get("X-Learny-Session")
            )
            session_id, session_history = session_store.get(requested_session_id)
            rate_session_id = _rate_session_id(self.headers.get("X-Learny-Rate-Session"))
            time_zone = self._rate_limit_time_zone()
            rate_limit_identity, rate_limit_size = _rate_limit_policy(account, rate_session_id)
            rate_limit = database.peek_rate_limit(
                rate_limit_identity,
                limit=rate_limit_size,
                window_ms=RATE_LIMIT_WINDOW_MS,
                time_zone=time_zone,
            )
            if not rate_limit.get("allowed", False):
                self._send_json(
                    {
                        "sessionId": session_id,
                        "rateSessionId": rate_session_id,
                        "error": GENERIC_ERROR_MESSAGE,
                        "retryable": False,
                        "rateLimit": _public_rate_limit(rate_limit),
                    },
                    HTTPStatus.TOO_MANY_REQUESTS,
                    extra_headers=[_retry_after_header(rate_limit)],
                )
                return

            if account is not None and chat_id:
                history = database.history_for_chat(int(account["id"]), chat_id, max_turns=8)
            else:
                history = session_history

            bot = Learny(
                generator=config.generator_factory(),
                history=history,
            )
            groq_message = _message_with_attachment_context(message, attachment_contexts)
            response = bot.reply(groq_message)

            if response.source == "unknown":
                self._send_json(
                    {
                        "sessionId": session_id,
                        "answer": response.answer,
                        "source": response.source,
                        "model": response.model,
                        "retryable": True,
                        "rateSessionId": rate_session_id,
                        "rateLimit": _public_rate_limit(rate_limit),
                    }
                )
                return

            rate_limit = database.consume_rate_limit(
                rate_limit_identity,
                limit=rate_limit_size,
                window_ms=RATE_LIMIT_WINDOW_MS,
                time_zone=time_zone,
            )
            if not rate_limit.get("allowed", False):
                self._send_json(
                    {
                        "sessionId": session_id,
                        "rateSessionId": rate_session_id,
                        "error": GENERIC_ERROR_MESSAGE,
                        "retryable": False,
                        "rateLimit": _public_rate_limit(rate_limit),
                    },
                    HTTPStatus.TOO_MANY_REQUESTS,
                    extra_headers=[_retry_after_header(rate_limit)],
                )
                return

            if account is not None and chat_id:
                database.ensure_chat(
                    int(account["id"]),
                    chat_id,
                    title=_chat_title_from_message(message),
                    session_id=session_id,
                )
                database.append_message(
                    int(account["id"]),
                    chat_id,
                    speaker="You",
                    text=message,
                    history_text=groq_message,
                    source="sent",
                )
                database.append_message(
                    int(account["id"]),
                    chat_id,
                    speaker="Learny",
                    text=response.answer,
                    source=response.source,
                )
            self._send_json(
                {
                    "sessionId": session_id,
                    "answer": response.answer,
                    "source": response.source,
                    "model": response.model,
                    "retryable": False,
                    "rateSessionId": rate_session_id,
                    "rateLimit": _public_rate_limit(rate_limit),
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

        def _current_account(self) -> dict[str, Any] | None:
            return database.get_account_for_session(self._account_session_token())

        def _require_admin_account(self) -> dict[str, Any] | None:
            account = self._current_account()
            if account is None:
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.UNAUTHORIZED)
                return None
            ban = self._current_ban(account)
            if ban:
                self._send_ban_response(ban)
                return None
            if not _is_admin_account(account):
                self._send_json({"error": GENERIC_ERROR_MESSAGE}, HTTPStatus.FORBIDDEN)
                return None
            return account

        def _current_ban(self, account: dict[str, Any] | None = None) -> dict[str, Any] | None:
            username = str(account["username"]) if account else None
            return self._ban_for(username=username)

        def _ban_for(self, *, username: str | None = None) -> dict[str, Any] | None:
            try:
                return database.ban_for(username=username, ip_address=self._client_ip())
            except AccountError:
                return None

        def _send_ban_response(self, ban: dict[str, Any]) -> None:
            self._send_json(
                {
                    "error": GENERIC_ERROR_MESSAGE,
                    "retryable": False,
                    "ban": _public_ban_from_database(ban, database),
                    "platform": _public_platform(database.platform_state()),
                },
                HTTPStatus.FORBIDDEN,
            )

        def _verify_captcha_from_body(self, body: dict[str, Any]) -> bool:
            return captcha.verify(_optional_string(body, "captchaToken"), self._client_ip())

        def _rate_limit_time_zone(self) -> str:
            return _request_time_zone(self.headers.get("X-Learny-Time-Zone"))

        def _client_ip(self) -> str:
            forwarded_for = self.headers.get("X-Forwarded-For", "")
            if forwarded_for:
                first_value = forwarded_for.split(",", 1)[0].strip()
                if first_value:
                    return first_value
            real_ip = self.headers.get("X-Real-IP", "").strip()
            if real_ip:
                return real_ip
            try:
                return str(self.client_address[0])
            except Exception:
                return "unknown"

        def _account_session_token(self) -> str | None:
            cookie = SimpleCookie()
            try:
                cookie.load(self.headers.get("Cookie", ""))
            except Exception:
                return None
            morsel = cookie.get(ACCOUNT_SESSION_COOKIE)
            if morsel is None:
                return None
            token = morsel.value.strip()
            return token or None

        def _read_ask_body(self) -> dict[str, Any]:
            content_type = self.headers.get("Content-Type", "")
            if content_type.lower().startswith("multipart/form-data"):
                return self._read_multipart_body(content_type)
            return self._read_json_body(max_bytes=ASK_JSON_MAX_BYTES)

        def _read_multipart_body(self, content_type: str) -> dict[str, Any]:
            boundary = _multipart_boundary(content_type)
            if not boundary:
                raise ValueError("Multipart boundary is required.")

            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                raise ValueError("Request body is required.")
            if content_length > ASK_MULTIPART_MAX_BYTES:
                raise ValueError("Request body is too large.")

            payload = self.rfile.read(content_length)
            fields, files = _parse_multipart_form(payload, boundary)
            if len(files) > ATTACHMENT_LIMIT:
                raise ValueError("Too many attachments.")
            body: dict[str, Any] = dict(fields)
            if files:
                body["attachments"] = files
            return body

        def _read_json_body(self, max_bytes: int = 64_000) -> dict[str, Any]:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0:
                raise ValueError("Request body is required.")
            if content_length > max_bytes:
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
            extra_headers: list[tuple[str, str]] | None = None,
        ) -> None:
            payload = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self._send_cors_headers()
            for header, value in extra_headers or []:
                self.send_header(header, value)
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
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Vary", "Origin")

        def _needs_cross_site_cookie(self) -> bool:
            origin = self.headers.get("Origin", "").strip()
            if not origin.startswith("https://") or not _is_allowed_cors_origin(origin):
                return False

            origin_host = (urlsplit(origin).hostname or "").lower()
            request_host = self.headers.get("Host", "").split(":", 1)[0].lower()
            return bool(origin_host and request_host and origin_host != request_host)

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
        captcha_site_key=os.environ.get("RECAPTCHA_SITE_KEY", "").strip(),
        captcha_secret_key=os.environ.get("RECAPTCHA_SECRET_KEY", "").strip(),
    )
    run_server(args.host, args.port, config)
    return 0


def _default_static_dir() -> Path:
    if (WASMER_SITE_DIR / "index.html").exists():
        return WASMER_SITE_DIR
    if (WASMER_APP_DIR / "index.html").exists():
        return WASMER_APP_DIR
    if (WASMER_ROOT / "index.html").exists():
        return WASMER_ROOT
    if (WASMER_ROOT / "web" / "index.html").exists():
        return WASMER_ROOT / "web"
    if (REPOSITORY_ROOT / "index.html").exists() and (REPOSITORY_ROOT / "app" / "web").is_dir():
        return REPOSITORY_ROOT
    if (DEFAULT_STATIC_ROOT / "index.html").exists():
        return DEFAULT_STATIC_ROOT
    return DEFAULT_STATIC_DIR


def _default_database_path() -> Path:
    configured = os.environ.get("LEARNY_DB_PATH", "").strip()
    if configured:
        return Path(configured)
    if Path("/data").exists():
        return Path("/data/learny.sqlite3")
    return DEFAULT_DATA_DIR / "learny.sqlite3"


def _verify_google_recaptcha(secret_key: str, token: str, remote_ip: str | None) -> bool:
    form_data: dict[str, str] = {
        "secret": secret_key,
        "response": token,
    }
    if remote_ip and remote_ip != "unknown":
        form_data["remoteip"] = remote_ip

    request = urllib.request.Request(
        RECAPTCHA_VERIFY_URL,
        data=urlencode(form_data).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return False
    return bool(isinstance(payload, dict) and payload.get("success") is True)


def _safe_static_path(static_dir: Path, route: str) -> Path:
    route = unquote(route).replace("\\", "/").lstrip("/")
    if not route:
        route = "index.html"
    if (
        _uses_root_static_layout(static_dir)
        and route not in PUBLIC_ROOT_FILES
        and not route.startswith(("web/", "icon_library/", "logos/", "app/web/", "app/icon_library/"))
    ):
        raise ValueError("Static path is not part of the public web files.")
    candidate = (static_dir / route).resolve()
    static_root = static_dir.resolve()
    if candidate == static_root or static_root not in candidate.parents:
        raise ValueError("Static path escaped the web directory.")
    return candidate


def _uses_root_static_layout(static_dir: Path) -> bool:
    return (static_dir / "index.html").is_file() and (
        (static_dir / "web").is_dir() or (static_dir / "app" / "web").is_dir()
    )


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


def _multipart_boundary(content_type: str) -> str | None:
    for part in content_type.split(";"):
        key, separator, value = part.strip().partition("=")
        if separator and key.strip().lower() == "boundary":
            return value.strip().strip('"')
    return None


def _parse_multipart_form(
    payload: bytes,
    boundary: str,
) -> tuple[dict[str, str], list[UploadedAttachment]]:
    boundary_bytes = f"--{boundary}".encode("utf-8")
    fields: dict[str, str] = {}
    files: list[UploadedAttachment] = []

    for raw_part in payload.split(boundary_bytes):
        part = raw_part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if part.endswith(b"--"):
            part = part[:-2].strip(b"\r\n")
        header_block, separator, content = part.partition(b"\r\n\r\n")
        if not separator:
            continue

        headers = _parse_multipart_headers(header_block)
        disposition = headers.get("content-disposition", "")
        disposition_value, disposition_params = _parse_header_value(disposition)
        if disposition_value.lower() != "form-data":
            continue

        field_name = disposition_params.get("name", "").strip()
        if not field_name:
            continue

        content = content.removesuffix(b"\r\n")
        filename = disposition_params.get("filename")
        if filename is None:
            fields[field_name] = content.decode("utf-8", errors="replace").strip()
            continue

        files.append(
            UploadedAttachment(
                field_name=field_name,
                filename=Path(filename.replace("\\", "/")).name,
                content_type=headers.get("content-type", "").strip(),
                data=content,
            )
        )

    return fields, files


def _parse_multipart_headers(header_block: bytes) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in header_block.decode("iso-8859-1", errors="replace").split("\r\n"):
        name, separator, value = line.partition(":")
        if separator:
            headers[name.strip().lower()] = value.strip()
    return headers


def _parse_header_value(value: str) -> tuple[str, dict[str, str]]:
    parts = [part.strip() for part in value.split(";") if part.strip()]
    if not parts:
        return "", {}

    params: dict[str, str] = {}
    for part in parts[1:]:
        key, separator, param_value = part.partition("=")
        if separator:
            params[key.strip().lower()] = param_value.strip().strip('"')
    return parts[0], params


def _attachment_contexts_from_body(body: dict[str, Any]) -> tuple[AttachmentContext, ...]:
    uploads = body.get("attachments")
    if uploads is None:
        upload = body.get("attachment")
        uploads = [] if upload is None else [upload]
    if not isinstance(uploads, list):
        raise ValueError("Attachments are invalid.")
    if len(uploads) > ATTACHMENT_LIMIT:
        raise ValueError("Too many attachments.")

    contexts: list[AttachmentContext] = []
    for upload in uploads:
        if not isinstance(upload, UploadedAttachment):
            raise ValueError("Attachment is invalid.")
        contexts.append(_extract_attachment_context(upload))
    return tuple(contexts)


def _extract_attachment_context(upload: UploadedAttachment) -> AttachmentContext:
    filename = upload.filename.strip()
    extension = _attachment_extension(filename)
    if extension not in SUPPORTED_ATTACHMENT_EXTENSIONS:
        raise ValueError("Attachment type is not supported.")
    if not upload.data or len(upload.data) > ATTACHMENT_MAX_BYTES:
        raise ValueError("Attachment is too large.")

    text = _extract_attachment_text(extension, upload.data)
    text = _clean_extracted_attachment_text(text)
    if not text:
        raise ValueError("Attachment text could not be extracted.")

    truncated = len(text) > ATTACHMENT_TEXT_MAX_CHARS
    if truncated:
        text = text[:ATTACHMENT_TEXT_MAX_CHARS].rstrip()

    return AttachmentContext(
        filename=filename,
        extension=extension,
        content_type=upload.content_type,
        size=len(upload.data),
        text=text,
        truncated=truncated,
    )


def _attachment_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    return suffix


def _extract_attachment_text(extension: str, data: bytes) -> str:
    if extension in PLAIN_TEXT_ATTACHMENT_EXTENSIONS:
        return _decode_text_bytes(data)
    if extension == "docx":
        return _extract_docx_text(data)
    if extension == "rtf":
        return _extract_rtf_text(data)
    if extension == "pdf":
        return _extract_pdf_text(data)
    raise ValueError("Attachment type is not supported.")


def _decode_text_bytes(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_docx_text(data: bytes) -> str:
    paragraphs: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            document_xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as error:
        raise ValueError("DOCX attachment is invalid.") from error

    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as error:
        raise ValueError("DOCX attachment is invalid.") from error

    for paragraph in root.iter():
        if _xml_local_name(paragraph.tag) != "p":
            continue
        chunks: list[str] = []
        for child in paragraph.iter():
            name = _xml_local_name(child.tag)
            if name == "t" and child.text:
                chunks.append(child.text)
            elif name == "tab":
                chunks.append("\t")
            elif name in {"br", "cr"}:
                chunks.append("\n")
        paragraph_text = "".join(chunks).strip()
        if paragraph_text:
            paragraphs.append(paragraph_text)
    return "\n".join(paragraphs)


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _extract_rtf_text(data: bytes) -> str:
    text = _decode_text_bytes(data)
    text = re.sub(
        r"\\'([0-9a-fA-F]{2})",
        lambda match: bytes.fromhex(match.group(1)).decode("cp1252", errors="replace"),
        text,
    )
    text = re.sub(r"\\par[d]?\b", "\n", text)
    text = re.sub(r"\\line\b", "\n", text)
    text = re.sub(r"\\tab\b", "\t", text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", text)
    text = re.sub(r"\\.", lambda match: match.group(0)[1:], text)
    text = text.replace("{", "").replace("}", "")
    return text


def _extract_pdf_text(data: bytes) -> str:
    chunks: list[str] = []
    for stream_data, compressed in _pdf_streams(data):
        if compressed:
            try:
                stream_data = zlib.decompress(stream_data.strip())
            except zlib.error:
                continue
        chunks.extend(_pdf_text_strings(stream_data))

    if not chunks:
        chunks.extend(_pdf_text_strings(data))
    return "\n".join(chunks)


def _pdf_streams(data: bytes) -> list[tuple[bytes, bool]]:
    streams: list[tuple[bytes, bool]] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, flags=re.DOTALL):
        stream_data = match.group(1)
        header_window = data[max(0, match.start() - 500):match.start()]
        compressed = b"/FlateDecode" in header_window
        streams.append((stream_data, compressed))
    return streams


def _pdf_text_strings(data: bytes) -> list[str]:
    raw = data.decode("latin-1", errors="ignore")
    strings: list[str] = []
    for literal in re.findall(r"\((?:\\.|[^\\()])*\)", raw, flags=re.DOTALL):
        clean = _decode_pdf_literal(literal[1:-1])
        if _looks_like_text(clean):
            strings.append(clean)
    for hex_value in re.findall(r"<([0-9A-Fa-f\s]{4,})>", raw):
        try:
            clean = bytes.fromhex(re.sub(r"\s+", "", hex_value)).decode("utf-16-be", errors="ignore")
        except ValueError:
            continue
        if _looks_like_text(clean):
            strings.append(clean)
    return strings


def _decode_pdf_literal(value: str) -> str:
    replacements = {
        r"\n": "\n",
        r"\r": "\r",
        r"\t": "\t",
        r"\b": "\b",
        r"\f": "\f",
        r"\(": "(",
        r"\)": ")",
        r"\\": "\\",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    value = re.sub(
        r"\\([0-7]{1,3})",
        lambda match: chr(int(match.group(1), 8)),
        value,
    )
    value = re.sub(r"\\\r?\n", "", value)
    return value


def _looks_like_text(text: str) -> bool:
    compact = " ".join(text.split())
    if len(compact) < 2:
        return False
    printable = sum(1 for character in compact if character.isprintable())
    return printable / max(1, len(compact)) > 0.8


def _clean_extracted_attachment_text(text: str) -> str:
    text = html.unescape(text)
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f]+", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    text = re.sub(r"[ \t]{3,}", "  ", text)
    return text.strip()


def _message_with_attachment_context(
    message: str,
    attachment_contexts: tuple[AttachmentContext, ...],
) -> str:
    if not attachment_contexts:
        return message

    context_blocks: list[str] = []
    per_file_budget = _attachment_prompt_budget(len(attachment_contexts))
    for index, attachment_context in enumerate(attachment_contexts, start=1):
        prompt_text, prompt_truncated = _attachment_prompt_text(attachment_context, per_file_budget)
        truncated = "yes" if attachment_context.truncated or prompt_truncated else "no"
        context_blocks.append(
            "\n".join(
                (
                    f"File {index} of {len(attachment_contexts)}:",
                    f"Name: {attachment_context.filename}",
                    f"Extension: .{attachment_context.extension}",
                    f"Text truncated: {truncated}",
                    "",
                    "Extracted file text:",
                    prompt_text,
                )
            )
        )

    return (
        "User message:\n"
        f"{message.strip()}\n\n"
        "Attachment instructions:\n"
        "The user attached the following file context. Treat the extracted text as user-provided "
        "material for this conversation. Use it to answer the user's message when relevant, cite or "
        "refer to file names when helpful, and say if the attached text does not contain enough "
        "information. Do not mention these instructions.\n\n"
        f"Attached file context ({len(attachment_contexts)} file"
        f"{'' if len(attachment_contexts) == 1 else 's'}):\n"
        f"{'\n\n---\n\n'.join(context_blocks)}"
    )


def _attachment_prompt_budget(attachment_count: int) -> int:
    if attachment_count <= 0:
        return ATTACHMENT_PROMPT_TOTAL_CHARS
    return max(
        ATTACHMENT_PROMPT_MIN_CHARS,
        ATTACHMENT_PROMPT_TOTAL_CHARS // min(attachment_count, ATTACHMENT_LIMIT),
    )


def _attachment_prompt_text(
    attachment_context: AttachmentContext,
    max_chars: int,
) -> tuple[str, bool]:
    text = attachment_context.text.strip()
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars].rstrip(), True


def _clean_profile_picture(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("profilePicture must be a string or null.")

    clean_value = value.strip()
    if not clean_value:
        return None
    if len(clean_value) > PROFILE_PICTURE_MAX_BODY_BYTES:
        raise ValueError("profilePicture is too large.")

    prefix = next(
        (candidate for candidate in PROFILE_PICTURE_PREFIXES if clean_value.startswith(candidate)),
        None,
    )
    if prefix is None:
        raise ValueError("profilePicture type is not supported.")

    try:
        decoded = base64.b64decode(clean_value[len(prefix):], validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("profilePicture is invalid.") from error

    if not decoded or len(decoded) > PROFILE_PICTURE_MAX_BYTES:
        raise ValueError("profilePicture is too large.")
    return clean_value


def _clean_session_id(session_id: str | None) -> str | None:
    if session_id is None:
        return None
    session_id = session_id.strip()
    if not session_id:
        return None
    return "".join(character for character in session_id if character.isalnum() or character in "-_")[:80]


def _public_account(account: dict[str, Any]) -> dict[str, Any]:
    profile_picture = account.get("profilePicture", account.get("profile_picture"))
    masked_email = _mask_email(account.get("email", account.get("email_address", "")))
    is_admin = _is_admin_account(account)
    attachments_verified_at = int(
        account.get("attachmentsVerifiedAt", account.get("attachments_verified_at", 0)) or 0
    )
    return {
        "username": str(account["username"]),
        "email": masked_email,
        "maskedEmail": masked_email,
        "profilePicture": str(profile_picture) if profile_picture else None,
        "createdAt": int(account["createdAt"]),
        "lastSeenAt": int(account["lastSeenAt"]),
        "isAdmin": is_admin,
        "canResetRateLimits": is_admin,
        "attachmentsVerified": attachments_verified_at > 0,
    }


def _rate_session_id(value: str | None) -> str:
    return _clean_session_id(value) or secrets.token_urlsafe(18)


def _request_time_zone(value: str | None) -> str:
    time_zone = str(value or "").strip()
    return time_zone[:80] if time_zone else DEFAULT_RATE_LIMIT_TIME_ZONE


def _rate_limit_policy(account: dict[str, Any] | None, rate_session_id: str = "") -> tuple[str, int]:
    if account is None:
        return f"session:{_rate_session_id(rate_session_id)}", GUEST_RATE_LIMIT_LIMIT
    return f"account:{int(account['id'])}", RATE_LIMIT_LIMIT


def _is_admin_account(account: dict[str, Any] | None) -> bool:
    if not account:
        return False
    username = str(account.get("username", ""))
    return bool(account.get("isAdmin")) or username.casefold() == DEFAULT_ADMIN_USERNAME.casefold()


def _is_owner_admin_account(account: dict[str, Any] | None) -> bool:
    if not account:
        return False
    return str(account.get("username", "")).casefold() == DEFAULT_ADMIN_USERNAME.casefold()


def _public_platform(platform: dict[str, Any]) -> dict[str, Any]:
    return {
        "available": bool(platform.get("available", True)),
        "updatedAt": int(platform.get("updatedAt", _now_ms())),
    }


def _account_lookup(database: Any) -> dict[str, dict[str, Any]]:
    try:
        accounts = database.list_accounts()
    except Exception:
        return {}
    return {
        str(account.get("username", "")).casefold(): account
        for account in accounts
        if account and account.get("username")
    }


def _account_by_username(database: Any, username: str) -> dict[str, Any] | None:
    clean_username = str(username).strip().casefold()
    if not clean_username:
        return None
    return _account_lookup(database).get(clean_username)


def _public_ban_from_database(ban: dict[str, Any] | None, database: Any) -> dict[str, Any] | None:
    return _public_ban(ban, _account_lookup(database))


def _public_ban(
    ban: dict[str, Any] | None,
    account_lookup: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    if not ban:
        return None
    created_by = str(ban.get("createdBy", "")).strip()
    actor_account = None
    if created_by:
        account = (account_lookup or {}).get(created_by.casefold())
        actor_account = {
            "username": str(account.get("username", created_by)) if account else created_by,
            "profilePicture": account.get("profilePicture") if account else None,
        }
    return {
        "kind": str(ban.get("kind", "")),
        "target": str(ban.get("target", "")),
        "reason": str(ban.get("reason", "")) or "Access was restricted by Learny moderation.",
        "createdAt": int(ban.get("createdAt", _now_ms())),
        "createdBy": created_by,
        "createdByAccount": actor_account,
    }


def _public_admin_account(
    account: dict[str, Any],
    account_lookup: dict[str, dict[str, Any]] | None = None,
    rate_limit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    public_rate_limit = _public_rate_limit(rate_limit) if rate_limit else None
    masked_email = _mask_email(account.get("email", ""))
    return {
        "username": str(account["username"]),
        "email": masked_email,
        "maskedEmail": masked_email,
        "profilePicture": account.get("profilePicture"),
        "createdAt": int(account["createdAt"]),
        "lastSeenAt": int(account["lastSeenAt"]),
        "isAdmin": bool(account.get("isAdmin")),
        "chatCount": int(account.get("chatCount", 0)),
        "messageCount": int(account.get("messageCount", 0)),
        "ban": _public_ban(account.get("ban"), account_lookup),
        "rateLimit": public_rate_limit,
        "rateLimitPercent": _rate_limit_percent(public_rate_limit),
    }


def _mask_email(email: Any) -> str:
    clean_email = str(email or "").strip()
    if not clean_email:
        return ""
    local, separator, domain = clean_email.partition("@")
    if not separator:
        return f"***{clean_email[3:]}"
    return f"***{local[3:]}@{domain}"


def _admin_portal_payload(
    database: Any,
    time_zone: str = DEFAULT_RATE_LIMIT_TIME_ZONE,
) -> dict[str, Any]:
    raw_accounts = database.list_accounts()
    account_lookup = {
        str(account.get("username", "")).casefold(): account
        for account in raw_accounts
        if account and account.get("username")
    }
    rate_limits: dict[str, dict[str, Any]] = {}
    for account in raw_accounts:
        identity_key, limit = _rate_limit_policy(account)
        if identity_key not in rate_limits:
            rate_limits[identity_key] = database.peek_rate_limit(
                identity_key,
                limit=limit,
                window_ms=RATE_LIMIT_WINDOW_MS,
                time_zone=time_zone,
            )
    accounts = [
        _public_admin_account(
            account,
            account_lookup,
            rate_limits.get(_rate_limit_policy(account)[0]),
        )
        for account in raw_accounts
    ]
    admins = [
        _public_admin_account(
            account,
            account_lookup,
            rate_limits.get(_rate_limit_policy(account)[0]),
        )
        for account in raw_accounts
        if account.get("isAdmin")
    ]
    bans = [_public_ban(ban, account_lookup) for ban in database.list_bans()]
    return {
        "adminPortal": {
            "platform": _public_platform(database.platform_state()),
            "accounts": accounts,
            "admins": admins,
            "bans": [ban for ban in bans if ban is not None],
        }
    }


def _public_rate_limit(rate_limit: dict[str, Any]) -> dict[str, Any]:
    return {
        "limit": int(rate_limit["limit"]),
        "remaining": int(rate_limit["remaining"]),
        "windowMs": int(rate_limit["windowMs"]),
        "resetAt": int(rate_limit["resetAt"]),
        "limited": bool(rate_limit["limited"]),
    }


def _rate_limit_percent(rate_limit: dict[str, Any] | None) -> int:
    if not rate_limit:
        return 100
    limit = int(rate_limit.get("limit", 0))
    remaining = int(rate_limit.get("remaining", 0))
    if limit <= 0 or remaining <= 0:
        return 0
    return max(1, min(100, round((remaining / limit) * 100)))


def _retry_after_header(rate_limit: dict[str, Any]) -> tuple[str, str]:
    reset_at = int(rate_limit.get("resetAt", _now_ms()))
    retry_after_seconds = max(1, (reset_at - _now_ms() + 999) // 1000)
    return ("Retry-After", str(retry_after_seconds))


def _now_ms() -> int:
    return int(time.time() * 1000)


def _account_cookie_header(token: str, cross_site: bool = False) -> tuple[str, str]:
    same_site = "SameSite=None; Secure" if cross_site else "SameSite=Lax"
    return (
        "Set-Cookie",
        (
            f"{ACCOUNT_SESSION_COOKIE}={token}; Path=/; HttpOnly; {same_site}; Max-Age=2592000"
        ),
    )


def _clear_account_cookie_header(cross_site: bool = False) -> tuple[str, str]:
    same_site = "SameSite=None; Secure" if cross_site else "SameSite=Lax"
    return (
        "Set-Cookie",
        f"{ACCOUNT_SESSION_COOKIE}=; Path=/; HttpOnly; {same_site}; Max-Age=0",
    )


def _chat_title_from_message(message: str) -> str:
    title = " ".join(message.strip().split())
    if not title:
        return "New chat"
    return title[:34] + ("..." if len(title) > 34 else "")
