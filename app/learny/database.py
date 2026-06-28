from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
import hashlib
import hmac
import secrets
import sqlite3
import sys
import threading
import time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .conversation import ConversationHistory


PASSWORD_ITERATIONS = 210_000
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30
RATE_LIMIT_LIMIT = 200
RATE_LIMIT_WINDOW_MS = 86_400_000
DEFAULT_RATE_LIMIT_TIME_ZONE = "UTC"
DEFAULT_ADMIN_USERNAME = "adamsrealm1"
PLATFORM_AVAILABLE_KEY = "learny_available"


def _add_vendor_time_zone_path() -> None:
    project_root = Path(__file__).resolve().parent.parent
    for vendor_path in (Path("/vendor"), Path("/app/vendor"), project_root / "vendor"):
        if vendor_path.is_dir():
            vendor_text = str(vendor_path)
            if vendor_text not in sys.path:
                sys.path.insert(0, vendor_text)


_add_vendor_time_zone_path()


class AccountError(ValueError):
    """Raised when account input is invalid or cannot be accepted."""


class AuthenticationError(ValueError):
    """Raised when a username/password pair cannot be authenticated."""


class LearnyDatabase:
    backend_name = "sqlite"

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    profile_picture TEXT,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    attachments_verified_at INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    last_seen_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS account_sessions (
                    token_hash TEXT PRIMARY KEY,
                    account_id INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT NOT NULL,
                    account_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (account_id, id),
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    chat_id TEXT NOT NULL,
                    speaker TEXT NOT NULL,
                    text TEXT NOT NULL,
                    history_text TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT '',
                    thought_seconds REAL,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (account_id, chat_id) REFERENCES chats(account_id, id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS account_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS rate_limit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identity_key TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rate_limit_time_zones (
                    lock_key TEXT PRIMARY KEY,
                    time_zone TEXT NOT NULL,
                    locked_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS moderation_bans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    target_key TEXT NOT NULL,
                    display_target TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    created_by TEXT NOT NULL DEFAULT '',
                    UNIQUE(kind, target_key)
                );

                CREATE TABLE IF NOT EXISTS platform_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_account_sessions_account_id
                    ON account_sessions(account_id);
                CREATE INDEX IF NOT EXISTS idx_chats_account_updated
                    ON chats(account_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_account_chat_id
                    ON messages(account_id, chat_id, id);
                CREATE INDEX IF NOT EXISTS idx_rate_limit_identity_created
                    ON rate_limit_events(identity_key, created_at);
                CREATE INDEX IF NOT EXISTS idx_moderation_bans_kind_target
                    ON moderation_bans(kind, target_key);
                """
            )
            self._ensure_profile_picture_column(connection)
            self._ensure_account_admin_column(connection)
            self._ensure_attachments_verified_column(connection)
            self._ensure_message_history_column(connection)
            self._ensure_default_admin(connection)
            self._ensure_platform_settings(connection)

    def _ensure_profile_picture_column(self, connection: sqlite3.Connection) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(accounts)").fetchall()
        }
        if "profile_picture" not in columns:
            connection.execute("ALTER TABLE accounts ADD COLUMN profile_picture TEXT")

    def _ensure_message_history_column(self, connection: sqlite3.Connection) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(messages)").fetchall()
        }
        if "history_text" not in columns:
            connection.execute("ALTER TABLE messages ADD COLUMN history_text TEXT NOT NULL DEFAULT ''")

    def _ensure_account_admin_column(self, connection: sqlite3.Connection) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(accounts)").fetchall()
        }
        if "is_admin" not in columns:
            connection.execute("ALTER TABLE accounts ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")

    def _ensure_attachments_verified_column(self, connection: sqlite3.Connection) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(accounts)").fetchall()
        }
        if "attachments_verified_at" not in columns:
            connection.execute(
                "ALTER TABLE accounts ADD COLUMN attachments_verified_at INTEGER NOT NULL DEFAULT 0"
            )

    def _ensure_default_admin(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            "UPDATE accounts SET is_admin = 1 WHERE username = ? COLLATE NOCASE",
            (DEFAULT_ADMIN_USERNAME,),
        )

    def _ensure_platform_settings(self, connection: sqlite3.Connection) -> None:
        now = _now_ms()
        connection.execute(
            """
            INSERT INTO platform_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO NOTHING
            """,
            (PLATFORM_AVAILABLE_KEY, "1", now),
        )

    def create_account(self, username: str, password: str) -> dict[str, Any]:
        username = _clean_username(username)
        _validate_password(password)
        salt = secrets.token_hex(16)
        password_hash = _hash_password(password, salt)
        now = _now_ms()

        with self._lock, self._connect() as connection:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO accounts
                        (username, password_salt, password_hash, profile_picture, is_admin, created_at, last_seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        salt,
                        password_hash,
                        None,
                        1 if _is_default_admin_username(username) else 0,
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise AccountError("Account could not be created.") from error

            account_id = int(cursor.lastrowid)
            connection.execute(
                "INSERT INTO account_events (account_id, event_type, created_at) VALUES (?, ?, ?)",
                (account_id, "created", now),
            )

        return {
            "id": account_id,
            "username": username,
            "profilePicture": None,
            "isAdmin": _is_default_admin_username(username),
            "attachmentsVerifiedAt": 0,
            "createdAt": now,
            "lastSeenAt": now,
        }

    def authenticate(self, username: str, password: str) -> dict[str, Any]:
        username = _clean_username(username)
        now = _now_ms()
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM accounts WHERE username = ?",
                (username,),
            ).fetchone()
            if row is None:
                raise AuthenticationError("Account could not be authenticated.")

            expected_hash = _hash_password(password, str(row["password_salt"]))
            if not hmac.compare_digest(expected_hash, str(row["password_hash"])):
                raise AuthenticationError("Account could not be authenticated.")

            connection.execute(
                "UPDATE accounts SET last_seen_at = ? WHERE id = ?",
                (now, int(row["id"])),
            )
            connection.execute(
                "INSERT INTO account_events (account_id, event_type, created_at) VALUES (?, ?, ?)",
                (int(row["id"]), "signed_in", now),
            )

        return {
            "id": int(row["id"]),
            "username": str(row["username"]),
            "profilePicture": row["profile_picture"],
            "isAdmin": _row_bool(row, "is_admin") or _is_default_admin_username(str(row["username"])),
            "attachmentsVerifiedAt": int(row["attachments_verified_at"]),
            "createdAt": int(row["created_at"]),
            "lastSeenAt": now,
        }

    def verify_password(self, account_id: int, password: str) -> bool:
        try:
            _validate_password(password)
        except AccountError:
            return False

        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT password_salt, password_hash FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()

        if row is None:
            return False
        expected_hash = _hash_password(password, str(row["password_salt"]))
        return hmac.compare_digest(expected_hash, str(row["password_hash"]))

    def attachments_verified(self, account_id: int) -> bool:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT attachments_verified_at FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
        if row is None:
            return False
        return int(row["attachments_verified_at"]) > 0

    def mark_attachments_verified(self, account_id: int) -> dict[str, Any]:
        now = _now_ms()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE accounts
                SET attachments_verified_at = CASE
                        WHEN attachments_verified_at > 0 THEN attachments_verified_at
                        ELSE ?
                    END,
                    last_seen_at = ?
                WHERE id = ?
                """,
                (now, now, account_id),
            )
            row = connection.execute(
                "SELECT * FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
        if row is None:
            raise AccountError("Account could not be updated.")
        return _account_from_row(row)

    def update_profile_picture(self, account_id: int, profile_picture: str | None) -> dict[str, Any]:
        now = _now_ms()
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE accounts SET profile_picture = ?, last_seen_at = ? WHERE id = ?",
                (profile_picture, now, account_id),
            )
            row = connection.execute(
                "SELECT * FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()

        if row is None:
            raise AccountError("Account could not be updated.")
        return {
            "id": int(row["id"]),
            "username": str(row["username"]),
            "profilePicture": row["profile_picture"],
            "isAdmin": _row_bool(row, "is_admin") or _is_default_admin_username(str(row["username"])),
            "attachmentsVerifiedAt": int(row["attachments_verified_at"]),
            "createdAt": int(row["created_at"]),
            "lastSeenAt": now,
        }

    def create_session(self, account_id: int) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        now = _now_ms()
        expires_at = now + SESSION_MAX_AGE_SECONDS * 1000

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO account_sessions (token_hash, account_id, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (token_hash, account_id, now, expires_at),
            )

        return token

    def delete_session(self, token: str | None) -> None:
        if not token:
            return
        with self._lock, self._connect() as connection:
            connection.execute(
                "DELETE FROM account_sessions WHERE token_hash = ?",
                (_hash_token(token),),
            )

    def delete_account(self, account_id: int) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM accounts WHERE id = ?", (account_id,))

    def get_account_for_session(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None

        now = _now_ms()
        with self._lock, self._connect() as connection:
            connection.execute(
                "DELETE FROM account_sessions WHERE expires_at <= ?",
                (now,),
            )
            row = connection.execute(
                """
                SELECT accounts.*
                FROM account_sessions
                JOIN accounts ON accounts.id = account_sessions.account_id
                WHERE account_sessions.token_hash = ? AND account_sessions.expires_at > ?
                """,
                (_hash_token(token), now),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE accounts SET last_seen_at = ? WHERE id = ?",
                (now, int(row["id"])),
            )

        return {
            "id": int(row["id"]),
            "username": str(row["username"]),
            "profilePicture": row["profile_picture"],
            "isAdmin": _row_bool(row, "is_admin") or _is_default_admin_username(str(row["username"])),
            "attachmentsVerifiedAt": int(row["attachments_verified_at"]),
            "createdAt": int(row["created_at"]),
            "lastSeenAt": now,
        }

    def account_stats(self, account_id: int) -> dict[str, int]:
        with self._lock, self._connect() as connection:
            chat_count = connection.execute(
                "SELECT COUNT(*) FROM chats WHERE account_id = ?",
                (account_id,),
            ).fetchone()[0]
            message_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM messages
                WHERE messages.account_id = ?
                """,
                (account_id,),
            ).fetchone()[0]
            session_count = connection.execute(
                "SELECT COUNT(*) FROM account_sessions WHERE account_id = ? AND expires_at > ?",
                (account_id, _now_ms()),
            ).fetchone()[0]

        return {
            "chats": int(chat_count),
            "messages": int(message_count),
            "sessions": int(session_count),
        }

    def list_accounts(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    accounts.id,
                    accounts.username,
                    accounts.profile_picture,
                    accounts.is_admin,
                    accounts.attachments_verified_at,
                    accounts.created_at,
                    accounts.last_seen_at,
                    COALESCE(chat_counts.value, 0) AS chat_count,
                    COALESCE(message_counts.value, 0) AS message_count
                FROM accounts
                LEFT JOIN (
                    SELECT account_id, COUNT(*) AS value
                    FROM chats
                    GROUP BY account_id
                ) AS chat_counts ON chat_counts.account_id = accounts.id
                LEFT JOIN (
                    SELECT account_id, COUNT(*) AS value
                    FROM messages
                    GROUP BY account_id
                ) AS message_counts ON message_counts.account_id = accounts.id
                ORDER BY accounts.last_seen_at DESC, accounts.created_at DESC
                """
            ).fetchall()
            bans = {
                str(row["target_key"]): _ban_from_row(row)
                for row in connection.execute(
                    "SELECT * FROM moderation_bans WHERE kind = ?",
                    ("username",),
                ).fetchall()
            }

        accounts: list[dict[str, Any]] = []
        for row in rows:
            account = _account_from_row(row)
            account["chatCount"] = int(row["chat_count"])
            account["messageCount"] = int(row["message_count"])
            account["ban"] = bans.get(str(account["username"]).casefold())
            accounts.append(account)
        return accounts

    def list_admins(self) -> list[dict[str, Any]]:
        return [account for account in self.list_accounts() if account.get("isAdmin")]

    def set_account_admin(self, username: str, is_admin: bool) -> dict[str, Any]:
        clean_username = _clean_username(username)
        if _is_default_admin_username(clean_username) and not is_admin:
            raise AccountError("The owner admin cannot be changed.")
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM accounts WHERE username = ?",
                (clean_username,),
            ).fetchone()
            if row is None:
                raise AccountError("Account could not be found.")
            connection.execute(
                "UPDATE accounts SET is_admin = ?, last_seen_at = ? WHERE id = ?",
                (1 if is_admin else 0, _now_ms(), int(row["id"])),
            )
            updated = connection.execute(
                "SELECT * FROM accounts WHERE id = ?",
                (int(row["id"]),),
            ).fetchone()

        if updated is None:
            raise AccountError("Account could not be updated.")
        return _account_from_row(updated)

    def delete_account_by_username(self, username: str) -> bool:
        clean_username = _clean_username(username)
        if _is_default_admin_username(clean_username):
            raise AccountError("The owner admin cannot be deleted.")
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM accounts WHERE username = ?",
                (clean_username,),
            )
            return bool(cursor.rowcount)

    def platform_state(self) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT value, updated_at FROM platform_settings WHERE key = ?",
                (PLATFORM_AVAILABLE_KEY,),
            ).fetchone()
            if row is None:
                self._ensure_platform_settings(connection)
                row = connection.execute(
                    "SELECT value, updated_at FROM platform_settings WHERE key = ?",
                    (PLATFORM_AVAILABLE_KEY,),
                ).fetchone()

        value = "1" if row is None else str(row["value"])
        updated_at = _now_ms() if row is None else int(row["updated_at"])
        return {"available": value == "1", "updatedAt": updated_at}

    def set_platform_available(self, available: bool) -> dict[str, Any]:
        now = _now_ms()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO platform_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (PLATFORM_AVAILABLE_KEY, "1" if available else "0", now),
            )
        return {"available": bool(available), "updatedAt": now}

    def list_bans(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM moderation_bans ORDER BY created_at DESC"
            ).fetchall()
        return [_ban_from_row(row) for row in rows]

    def ban_identity(
        self,
        kind: str,
        target: str,
        reason: str,
        *,
        created_by: str = "",
    ) -> dict[str, Any]:
        clean_kind = _clean_ban_kind(kind)
        display_target, target_key = _clean_ban_target(clean_kind, target)
        clean_reason = _clean_ban_reason(reason)
        clean_created_by = " ".join(str(created_by).strip().split())[:80]
        now = _now_ms()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO moderation_bans
                    (kind, target_key, display_target, reason, created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(kind, target_key) DO UPDATE SET
                    display_target = excluded.display_target,
                    reason = excluded.reason,
                    created_at = excluded.created_at,
                    created_by = excluded.created_by
                """,
                (clean_kind, target_key, display_target, clean_reason, now, clean_created_by),
            )
            row = connection.execute(
                "SELECT * FROM moderation_bans WHERE kind = ? AND target_key = ?",
                (clean_kind, target_key),
            ).fetchone()
        if row is None:
            raise AccountError("Ban could not be saved.")
        return _ban_from_row(row)

    def unban_identity(self, kind: str, target: str) -> bool:
        clean_kind = _clean_ban_kind(kind)
        _, target_key = _clean_ban_target(clean_kind, target)
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM moderation_bans WHERE kind = ? AND target_key = ?",
                (clean_kind, target_key),
            )
            return bool(cursor.rowcount)

    def ban_for(self, *, username: str | None = None, ip_address: str | None = None) -> dict[str, Any] | None:
        candidates: list[tuple[str, str]] = []
        if username:
            display_target, target_key = _clean_ban_target("username", username)
            candidates.append(("username", target_key))
        if ip_address:
            display_target, target_key = _clean_ban_target("ip", ip_address)
            candidates.append(("ip", target_key))
        if not candidates:
            return None

        with self._lock, self._connect() as connection:
            for kind, target_key in candidates:
                row = connection.execute(
                    "SELECT * FROM moderation_bans WHERE kind = ? AND target_key = ?",
                    (kind, target_key),
                ).fetchone()
                if row is not None:
                    return _ban_from_row(row)
        return None

    def peek_rate_limit(
        self,
        identity_key: str,
        *,
        limit: int = RATE_LIMIT_LIMIT,
        window_ms: int = RATE_LIMIT_WINDOW_MS,
        time_zone: str = DEFAULT_RATE_LIMIT_TIME_ZONE,
    ) -> dict[str, Any]:
        clean_identity_key = _clean_rate_limit_identity(identity_key)
        with self._lock, self._connect() as connection:
            return _sqlite_rate_limit_snapshot(
                connection,
                clean_identity_key,
                consume=False,
                limit=limit,
                window_ms=window_ms,
                time_zone=time_zone,
            )

    def consume_rate_limit(
        self,
        identity_key: str,
        *,
        limit: int = RATE_LIMIT_LIMIT,
        window_ms: int = RATE_LIMIT_WINDOW_MS,
        time_zone: str = DEFAULT_RATE_LIMIT_TIME_ZONE,
    ) -> dict[str, Any]:
        clean_identity_key = _clean_rate_limit_identity(identity_key)
        with self._lock, self._connect() as connection:
            return _sqlite_rate_limit_snapshot(
                connection,
                clean_identity_key,
                consume=True,
                limit=limit,
                window_ms=window_ms,
                time_zone=time_zone,
            )

    def clear_rate_limits(self) -> int:
        with self._lock, self._connect() as connection:
            cursor = connection.execute("DELETE FROM rate_limit_events")
            return int(cursor.rowcount if cursor.rowcount is not None else 0)

    def clear_rate_limit(self, identity_key: str) -> int:
        clean_identity_key = _clean_rate_limit_identity(identity_key)
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM rate_limit_events WHERE identity_key = ?",
                (clean_identity_key,),
            )
            return int(cursor.rowcount if cursor.rowcount is not None else 0)

    def locked_rate_limit_time_zone(self, lock_key: str, requested_time_zone: str | None) -> str:
        clean_lock_key = _clean_rate_limit_identity(lock_key)
        clean_time_zone = _clean_rate_limit_time_zone(requested_time_zone)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO rate_limit_time_zones (lock_key, time_zone, locked_at)
                VALUES (?, ?, ?)
                """,
                (clean_lock_key, clean_time_zone, _now_ms()),
            )
            row = connection.execute(
                "SELECT time_zone FROM rate_limit_time_zones WHERE lock_key = ?",
                (clean_lock_key,),
            ).fetchone()
        if row is None:
            return clean_time_zone
        return _clean_rate_limit_time_zone(str(row["time_zone"]))

    def rate_limit_time_zone(self, lock_key: str, fallback_time_zone: str | None = None) -> str:
        clean_lock_key = _clean_rate_limit_identity(lock_key)
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT time_zone FROM rate_limit_time_zones WHERE lock_key = ?",
                (clean_lock_key,),
            ).fetchone()
        if row is None:
            return _clean_rate_limit_time_zone(fallback_time_zone)
        return _clean_rate_limit_time_zone(str(row["time_zone"]))

    def list_chats(self, account_id: int) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            chat_rows = connection.execute(
                """
                SELECT id, title, session_id, created_at, updated_at
                FROM chats
                WHERE account_id = ?
                ORDER BY updated_at DESC
                """,
                (account_id,),
            ).fetchall()
            message_rows = connection.execute(
                """
                SELECT messages.chat_id, messages.speaker, messages.text, messages.source,
                       messages.thought_seconds, messages.created_at
                FROM messages
                WHERE messages.account_id = ?
                ORDER BY messages.id
                """,
                (account_id,),
            ).fetchall()

        messages_by_chat: dict[str, list[dict[str, Any]]] = {}
        for row in message_rows:
            messages_by_chat.setdefault(str(row["chat_id"]), []).append(_message_from_row(row))

        return [
            {
                "id": str(row["id"]),
                "title": str(row["title"]),
                "sessionId": str(row["session_id"]),
                "createdAt": int(row["created_at"]),
                "updatedAt": int(row["updated_at"]),
                "messages": messages_by_chat.get(str(row["id"]), []),
            }
            for row in chat_rows
        ]

    def replace_account_chats(self, account_id: int, chats: list[dict[str, Any]]) -> list[dict[str, Any]]:
        clean_chats = [_clean_chat_payload(chat) for chat in chats[:250]]
        incoming_ids = [chat["id"] for chat in clean_chats]

        with self._lock, self._connect() as connection:
            if incoming_ids:
                placeholders = ",".join("?" for _ in incoming_ids)
                connection.execute(
                    f"DELETE FROM chats WHERE account_id = ? AND id NOT IN ({placeholders})",
                    (account_id, *incoming_ids),
                )
            else:
                connection.execute("DELETE FROM chats WHERE account_id = ?", (account_id,))

            for chat in clean_chats:
                connection.execute(
                    """
                    INSERT INTO chats (id, account_id, title, session_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(account_id, id) DO UPDATE SET
                        title = excluded.title,
                        session_id = excluded.session_id,
                        updated_at = excluded.updated_at
                    """,
                    (
                        chat["id"],
                        account_id,
                        chat["title"],
                        chat["sessionId"],
                        chat["createdAt"],
                        chat["updatedAt"],
                    ),
                )
                existing_messages = connection.execute(
                    """
                    SELECT speaker, text, history_text
                    FROM messages
                    WHERE account_id = ? AND chat_id = ?
                    ORDER BY id
                    """,
                    (account_id, chat["id"]),
                ).fetchall()
                messages = _messages_with_preserved_history_text(chat["messages"], existing_messages)
                connection.execute(
                    "DELETE FROM messages WHERE account_id = ? AND chat_id = ?",
                    (account_id, chat["id"]),
                )
                connection.executemany(
                    """
                    INSERT INTO messages
                        (account_id, chat_id, speaker, text, history_text, source, thought_seconds, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            account_id,
                            chat["id"],
                            message["speaker"],
                            message["text"],
                            message["historyText"],
                            message["source"],
                            message["thoughtSeconds"],
                            message["createdAt"],
                        )
                        for message in messages
                    ],
                )

        return self.list_chats(account_id)

    def ensure_chat(
        self,
        account_id: int,
        chat_id: str,
        *,
        title: str,
        session_id: str,
    ) -> None:
        clean_chat_id = _clean_identifier(chat_id, "chat")
        clean_session_id = _clean_identifier(session_id, "session")
        clean_title = _clean_title(title)
        now = _now_ms()

        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chats (id, account_id, title, session_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id, id) DO UPDATE SET
                    title = CASE WHEN chats.title = 'New chat' THEN excluded.title ELSE chats.title END,
                    session_id = excluded.session_id,
                    updated_at = excluded.updated_at
                """,
                (clean_chat_id, account_id, clean_title, clean_session_id, now, now),
            )

    def append_message(
        self,
        account_id: int,
        chat_id: str,
        *,
        speaker: str,
        text: str,
        source: str = "",
        thought_seconds: float | None = None,
        history_text: str | None = None,
    ) -> None:
        clean_chat_id = _clean_identifier(chat_id, "chat")
        clean_message = _clean_message_payload(
            {
                "speaker": speaker,
                "text": text,
                "historyText": history_text,
                "source": source,
                "thoughtSeconds": thought_seconds,
                "createdAt": _now_ms(),
            }
        )

        with self._lock, self._connect() as connection:
            chat_exists = connection.execute(
                "SELECT 1 FROM chats WHERE id = ? AND account_id = ?",
                (clean_chat_id, account_id),
            ).fetchone()
            if chat_exists is None:
                return
            connection.execute(
                """
                INSERT INTO messages
                    (account_id, chat_id, speaker, text, history_text, source, thought_seconds, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account_id,
                    clean_chat_id,
                    clean_message["speaker"],
                    clean_message["text"],
                    clean_message["historyText"],
                    clean_message["source"],
                    clean_message["thoughtSeconds"],
                    clean_message["createdAt"],
                ),
            )
            connection.execute(
                "UPDATE chats SET updated_at = ? WHERE id = ? AND account_id = ?",
                (_now_ms(), clean_chat_id, account_id),
            )

    def history_for_chat(self, account_id: int, chat_id: str, max_turns: int = 8) -> ConversationHistory:
        clean_chat_id = _clean_identifier(chat_id, "chat")
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT messages.speaker, messages.text, messages.history_text
                FROM messages
                WHERE messages.account_id = ? AND messages.chat_id = ?
                ORDER BY messages.id
                """,
                (account_id, clean_chat_id),
            ).fetchall()

        history = ConversationHistory(max_turns=max_turns)
        pending_user = ""
        for row in rows:
            speaker = str(row["speaker"])
            text = str(row["text"])
            if speaker == "You":
                history_text = str(row["history_text"] or "").strip()
                pending_user = history_text or text
            elif speaker == "Learny" and pending_user:
                history.add(pending_user, text)
                pending_user = ""
        return history


def _clean_username(username: str) -> str:
    cleaned = " ".join(str(username).strip().split())
    if len(cleaned) < 3 or len(cleaned) > 24:
        raise AccountError("Account input is invalid.")
    if not all(character.isalnum() or character in "-_" for character in cleaned):
        raise AccountError("Account input is invalid.")
    return cleaned


def _is_default_admin_username(username: str) -> bool:
    return str(username).casefold() == DEFAULT_ADMIN_USERNAME.casefold()


def _row_bool(row: Any, key: str) -> bool:
    try:
        return bool(int(row[key]))
    except (KeyError, IndexError, TypeError, ValueError):
        return False


def _account_from_row(row: Any) -> dict[str, Any]:
    username = _row_string(row, "username")
    profile_picture = _row_string(row, "profile_picture").strip()
    is_admin = _row_bool(row, "is_admin") or _is_default_admin_username(username)
    return {
        "id": int(row["id"]),
        "username": username,
        "profilePicture": profile_picture or None,
        "isAdmin": is_admin,
        "attachmentsVerifiedAt": int(row["attachments_verified_at"]),
        "createdAt": int(row["created_at"]),
        "lastSeenAt": int(row["last_seen_at"]),
    }


def _clean_ban_kind(kind: str) -> str:
    clean_kind = str(kind).strip().casefold()
    if clean_kind not in {"username", "ip"}:
        raise AccountError("Ban type is invalid.")
    return clean_kind


def _clean_ban_target(kind: str, target: str) -> tuple[str, str]:
    clean_kind = _clean_ban_kind(kind)
    if clean_kind == "username":
        display_target = _clean_username(target)
        return display_target, display_target.casefold()

    display_target = " ".join(str(target).strip().split())
    if len(display_target) < 2 or len(display_target) > 80:
        raise AccountError("Ban target is invalid.")
    if not all(character.isalnum() or character in ".:-_" for character in display_target):
        raise AccountError("Ban target is invalid.")
    return display_target, display_target.casefold()


def _clean_ban_reason(reason: str) -> str:
    clean_reason = " ".join(str(reason).strip().split())
    if not clean_reason:
        clean_reason = "Access was restricted by Learny moderation."
    return clean_reason[:240]


def _ban_from_row(row: Any) -> dict[str, Any]:
    return {
        "kind": _row_string(row, "kind"),
        "target": _row_string(row, "display_target"),
        "targetKey": _row_string(row, "target_key"),
        "reason": _row_string(row, "reason") or "Access was restricted by Learny moderation.",
        "createdAt": int(row["created_at"]),
        "createdBy": _row_string(row, "created_by"),
    }


def _validate_password(password: str) -> None:
    if not isinstance(password, str) or len(password) < 8 or len(password) > 256:
        raise AccountError("Account input is invalid.")


def _hash_password(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    )
    return digest.hex()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now_ms() -> int:
    return int(time.time() * 1000)


def _clean_identifier(value: str, fallback_prefix: str) -> str:
    clean_value = "".join(
        character for character in str(value).strip() if character.isalnum() or character in "-_"
    )
    if clean_value:
        return clean_value[:120]
    return f"{fallback_prefix}-{secrets.token_urlsafe(12)}"


def _clean_title(value: str) -> str:
    title = " ".join(str(value).strip().split())
    if not title:
        return "New chat"
    return title[:80]


def _clean_chat_payload(chat: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(chat, dict):
        chat = {}
    now = _now_ms()
    chat_id = _clean_identifier(str(chat.get("id", "")), "chat")
    messages = chat.get("messages")
    if not isinstance(messages, list):
        messages = []

    return {
        "id": chat_id,
        "title": _clean_title(str(chat.get("title", "New chat"))),
        "sessionId": _clean_identifier(str(chat.get("sessionId", "")), "session"),
        "createdAt": _clean_timestamp(chat.get("createdAt"), now),
        "updatedAt": _clean_timestamp(chat.get("updatedAt"), now),
        "messages": [_clean_message_payload(message) for message in messages[:1000]],
    }


def _clean_message_payload(message: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(message, dict):
        message = {}
    now = _now_ms()
    speaker = str(message.get("speaker", "")).strip()
    if speaker not in {"You", "Learny"}:
        speaker = "Learny"
    text = str(message.get("text", "")).strip()
    if len(text) > 20_000:
        text = text[:20_000]
    source = str(message.get("source", "")).strip()[:80]
    history_text = _clean_history_text(message.get("historyText"), fallback=text)
    thought_seconds = _clean_thought_seconds(message.get("thoughtSeconds"))
    return {
        "speaker": speaker,
        "text": text,
        "historyText": history_text,
        "source": source,
        "thoughtSeconds": thought_seconds,
        "createdAt": _clean_timestamp(message.get("createdAt"), now),
    }


def _clean_history_text(value: Any, *, fallback: str) -> str:
    if value is None:
        text = fallback
    else:
        text = str(value).strip()
    if not text:
        text = fallback
    if len(text) > 40_000:
        text = text[:40_000]
    return text


def _messages_with_preserved_history_text(
    messages: list[dict[str, Any]],
    existing_rows: list[Any],
) -> list[dict[str, Any]]:
    preserved: list[dict[str, Any]] = []
    used_existing_indices: set[int] = set()
    for message in messages:
        next_message = dict(message)
        fallback = str(next_message["text"])
        history_text = _clean_history_text(next_message.get("historyText"), fallback=fallback)
        incoming_score = _history_text_score(history_text, fallback)
        best_existing_index: int | None = None
        best_existing_text = ""
        best_existing_score = -1

        for index, row in enumerate(existing_rows):
            if index in used_existing_indices:
                continue
            if (
                _row_string(row, "speaker") != str(next_message["speaker"])
                or _row_string(row, "text") != str(next_message["text"])
            ):
                continue
            candidate_text = _clean_history_text(_row_string(row, "history_text"), fallback=fallback)
            candidate_score = _history_text_score(candidate_text, fallback)
            if candidate_score > best_existing_score:
                best_existing_index = index
                best_existing_text = candidate_text
                best_existing_score = candidate_score

        if best_existing_index is not None:
            used_existing_indices.add(best_existing_index)
        if best_existing_score > incoming_score:
            history_text = best_existing_text
        next_message["historyText"] = history_text
        preserved.append(next_message)
    return preserved


def _history_text_score(history_text: str, fallback: str) -> int:
    clean_history_text = str(history_text).strip()
    clean_fallback = str(fallback).strip()
    if not clean_history_text:
        return 0
    score = min(len(clean_history_text), 40_000)
    if clean_history_text != clean_fallback:
        score += 100_000
    if "Attachment instructions:" in clean_history_text:
        score += 100_000
    return score


def _row_string(row: Any, key: str) -> str:
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        return ""
    return "" if value is None else str(value)


def _clean_timestamp(value: Any, fallback: int) -> int:
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        return fallback
    if timestamp <= 0:
        return fallback
    return timestamp


def _clean_thought_seconds(value: Any) -> float | None:
    if value is None:
        return None
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    return round(seconds, 1)


def _clean_rate_limit_identity(identity_key: str) -> str:
    clean_value = str(identity_key).strip()
    if len(clean_value) < 3 or len(clean_value) > 160:
        raise AccountError("Rate limit identity is invalid.")
    if not all(character.isalnum() or character in ":-_" for character in clean_value):
        raise AccountError("Rate limit identity is invalid.")
    return clean_value


def _clean_rate_limit_time_zone(time_zone: str | None) -> str:
    clean_value = str(time_zone or "").strip()
    if not clean_value or len(clean_value) > 80:
        return DEFAULT_RATE_LIMIT_TIME_ZONE
    if not all(character.isalnum() or character in "/_+-" for character in clean_value):
        return DEFAULT_RATE_LIMIT_TIME_ZONE
    try:
        ZoneInfo(clean_value)
    except ZoneInfoNotFoundError:
        return DEFAULT_RATE_LIMIT_TIME_ZONE
    return clean_value


def _rate_limit_payload(
    *,
    active_timestamps: list[int],
    allowed: bool,
    limit: int,
    window_ms: int,
    reset_at: int,
) -> dict[str, Any]:
    active_timestamps.sort()
    active_count = len(active_timestamps)
    remaining = max(0, limit - active_count)
    return {
        "limit": limit,
        "remaining": remaining,
        "windowMs": window_ms,
        "resetAt": reset_at,
        "limited": remaining <= 0,
        "allowed": allowed,
    }


def _rate_limit_window(
    now: int,
    time_zone: str = DEFAULT_RATE_LIMIT_TIME_ZONE,
) -> tuple[int, int, int]:
    local_time_zone = ZoneInfo(_clean_rate_limit_time_zone(time_zone))
    local_now = datetime.fromtimestamp(now / 1000, local_time_zone)
    window_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    reset_at = window_start + timedelta(days=1)
    window_start_ms = int(window_start.timestamp() * 1000)
    reset_at_ms = int(reset_at.timestamp() * 1000)
    return window_start_ms, reset_at_ms, reset_at_ms - window_start_ms


def _sqlite_rate_limit_snapshot(
    connection: sqlite3.Connection,
    identity_key: str,
    *,
    consume: bool,
    limit: int,
    window_ms: int,
    time_zone: str,
) -> dict[str, Any]:
    now = _now_ms()
    window_start, reset_at, actual_window_ms = _rate_limit_window(now, time_zone)
    connection.execute(
        """
        DELETE FROM rate_limit_events
        WHERE identity_key = ? AND (created_at < ? OR created_at >= ?)
        """,
        (identity_key, window_start, reset_at),
    )
    rows = connection.execute(
        """
        SELECT created_at
        FROM rate_limit_events
        WHERE identity_key = ? AND created_at >= ? AND created_at < ?
        ORDER BY created_at ASC
        """,
        (identity_key, window_start, reset_at),
    ).fetchall()
    active_timestamps = [int(row["created_at"]) for row in rows]

    if len(active_timestamps) >= limit:
        return _rate_limit_payload(
            active_timestamps=active_timestamps,
            allowed=False,
            limit=limit,
            window_ms=actual_window_ms,
            reset_at=reset_at,
        )

    if consume:
        connection.execute(
            "INSERT INTO rate_limit_events (identity_key, created_at) VALUES (?, ?)",
            (identity_key, now),
        )
        active_timestamps.append(now)

    return _rate_limit_payload(
        active_timestamps=active_timestamps,
        allowed=True,
        limit=limit,
        window_ms=actual_window_ms,
        reset_at=reset_at,
    )


def _message_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "speaker": str(row["speaker"]),
        "text": str(row["text"]),
        "source": str(row["source"]),
        "thoughtSeconds": row["thought_seconds"],
        "createdAt": int(row["created_at"]),
    }
