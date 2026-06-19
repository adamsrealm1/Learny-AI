from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import hashlib
import hmac
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from .conversation import ConversationHistory


PASSWORD_ITERATIONS = 210_000
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30
RATE_LIMIT_LIMIT = 200
RATE_LIMIT_WINDOW_MS = 86_400_000


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

                CREATE INDEX IF NOT EXISTS idx_account_sessions_account_id
                    ON account_sessions(account_id);
                CREATE INDEX IF NOT EXISTS idx_chats_account_updated
                    ON chats(account_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_messages_account_chat_id
                    ON messages(account_id, chat_id, id);
                CREATE INDEX IF NOT EXISTS idx_rate_limit_identity_created
                    ON rate_limit_events(identity_key, created_at);
                """
            )
            self._ensure_profile_picture_column(connection)

    def _ensure_profile_picture_column(self, connection: sqlite3.Connection) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(accounts)").fetchall()
        }
        if "profile_picture" not in columns:
            connection.execute("ALTER TABLE accounts ADD COLUMN profile_picture TEXT")

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
                    INSERT INTO accounts (username, password_salt, password_hash, created_at, last_seen_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (username, salt, password_hash, now, now),
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
            "createdAt": int(row["created_at"]),
            "lastSeenAt": now,
        }

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

    def peek_rate_limit(
        self,
        identity_key: str,
        *,
        limit: int = RATE_LIMIT_LIMIT,
        window_ms: int = RATE_LIMIT_WINDOW_MS,
    ) -> dict[str, Any]:
        clean_identity_key = _clean_rate_limit_identity(identity_key)
        with self._lock, self._connect() as connection:
            return _sqlite_rate_limit_snapshot(
                connection,
                clean_identity_key,
                consume=False,
                limit=limit,
                window_ms=window_ms,
            )

    def consume_rate_limit(
        self,
        identity_key: str,
        *,
        limit: int = RATE_LIMIT_LIMIT,
        window_ms: int = RATE_LIMIT_WINDOW_MS,
    ) -> dict[str, Any]:
        clean_identity_key = _clean_rate_limit_identity(identity_key)
        with self._lock, self._connect() as connection:
            return _sqlite_rate_limit_snapshot(
                connection,
                clean_identity_key,
                consume=True,
                limit=limit,
                window_ms=window_ms,
            )

    def clear_rate_limits(self) -> int:
        with self._lock, self._connect() as connection:
            cursor = connection.execute("DELETE FROM rate_limit_events")
            return int(cursor.rowcount if cursor.rowcount is not None else 0)

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
                connection.execute(
                    "DELETE FROM messages WHERE account_id = ? AND chat_id = ?",
                    (account_id, chat["id"]),
                )
                connection.executemany(
                    """
                    INSERT INTO messages (account_id, chat_id, speaker, text, source, thought_seconds, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            account_id,
                            chat["id"],
                            message["speaker"],
                            message["text"],
                            message["source"],
                            message["thoughtSeconds"],
                            message["createdAt"],
                        )
                        for message in chat["messages"]
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
    ) -> None:
        clean_chat_id = _clean_identifier(chat_id, "chat")
        clean_message = _clean_message_payload(
            {
                "speaker": speaker,
                "text": text,
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
                INSERT INTO messages (account_id, chat_id, speaker, text, source, thought_seconds, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account_id,
                    clean_chat_id,
                    clean_message["speaker"],
                    clean_message["text"],
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
                SELECT messages.speaker, messages.text
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
                pending_user = text
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
    thought_seconds = _clean_thought_seconds(message.get("thoughtSeconds"))
    return {
        "speaker": speaker,
        "text": text,
        "source": source,
        "thoughtSeconds": thought_seconds,
        "createdAt": _clean_timestamp(message.get("createdAt"), now),
    }


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


def _rate_limit_payload(
    *,
    active_timestamps: list[int],
    now: int,
    allowed: bool,
    limit: int,
    window_ms: int,
) -> dict[str, Any]:
    active_timestamps.sort()
    active_count = len(active_timestamps)
    remaining = max(0, limit - active_count)
    reset_at = (
        active_timestamps[0] + window_ms
        if active_timestamps
        else now + window_ms
    )
    return {
        "limit": limit,
        "remaining": remaining,
        "windowMs": window_ms,
        "resetAt": reset_at,
        "limited": remaining <= 0,
        "allowed": allowed,
    }


def _sqlite_rate_limit_snapshot(
    connection: sqlite3.Connection,
    identity_key: str,
    *,
    consume: bool,
    limit: int,
    window_ms: int,
) -> dict[str, Any]:
    now = _now_ms()
    window_start = now - window_ms
    connection.execute("DELETE FROM rate_limit_events WHERE created_at <= ?", (window_start,))
    rows = connection.execute(
        """
        SELECT created_at
        FROM rate_limit_events
        WHERE identity_key = ? AND created_at > ?
        ORDER BY created_at ASC
        """,
        (identity_key, window_start),
    ).fetchall()
    active_timestamps = [int(row["created_at"]) for row in rows]

    if len(active_timestamps) >= limit:
        return _rate_limit_payload(
            active_timestamps=active_timestamps,
            now=now,
            allowed=False,
            limit=limit,
            window_ms=window_ms,
        )

    if consume:
        connection.execute(
            "INSERT INTO rate_limit_events (identity_key, created_at) VALUES (?, ?)",
            (identity_key, now),
        )
        active_timestamps.append(now)

    return _rate_limit_payload(
        active_timestamps=active_timestamps,
        now=now,
        allowed=True,
        limit=limit,
        window_ms=window_ms,
    )


def _message_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "speaker": str(row["speaker"]),
        "text": str(row["text"]),
        "source": str(row["source"]),
        "thoughtSeconds": row["thought_seconds"],
        "createdAt": int(row["created_at"]),
    }
