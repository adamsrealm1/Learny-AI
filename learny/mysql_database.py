from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os
import secrets
import hmac
import sys
import threading
from pathlib import Path
from typing import Any

from .conversation import ConversationHistory
from .database import (
    RATE_LIMIT_LIMIT,
    RATE_LIMIT_WINDOW_MS,
    SESSION_MAX_AGE_SECONDS,
    AccountError,
    AuthenticationError,
    _clean_chat_payload,
    _clean_identifier,
    _clean_message_payload,
    _clean_rate_limit_identity,
    _clean_title,
    _clean_username,
    _hash_password,
    _hash_token,
    _message_from_row,
    _now_ms,
    _rate_limit_payload,
    _validate_password,
)


class MySQLLearnyDatabase:
    backend_name = "wasmer-mysql"

    def __init__(
        self,
        *,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        ssl_enabled: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.ssl_enabled = ssl_enabled
        self._lock = threading.RLock()
        self._pymysql = _load_pymysql()
        self._initialize()

    @classmethod
    def from_env(cls) -> "MySQLLearnyDatabase":
        config = mysql_config_from_env()
        if config is None:
            raise RuntimeError("Wasmer database environment variables are not configured.")
        return cls(**config)

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        connection = self._pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            autocommit=False,
            connect_timeout=10,
            read_timeout=30,
            write_timeout=30,
            cursorclass=self._pymysql.cursors.DictCursor,
            ssl={} if self.ssl_enabled else None,
        )
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                username VARCHAR(24) NOT NULL,
                username_key VARCHAR(24) NOT NULL,
                password_salt VARCHAR(64) NOT NULL,
                password_hash VARCHAR(128) NOT NULL,
                profile_picture MEDIUMTEXT NULL,
                created_at BIGINT NOT NULL,
                last_seen_at BIGINT NOT NULL,
                PRIMARY KEY (id),
                UNIQUE KEY uq_accounts_username_key (username_key)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS account_sessions (
                token_hash CHAR(64) NOT NULL,
                account_id BIGINT UNSIGNED NOT NULL,
                created_at BIGINT NOT NULL,
                expires_at BIGINT NOT NULL,
                PRIMARY KEY (token_hash),
                KEY idx_account_sessions_account_id (account_id),
                CONSTRAINT fk_account_sessions_account
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS chats (
                id VARCHAR(120) NOT NULL,
                account_id BIGINT UNSIGNED NOT NULL,
                title VARCHAR(80) NOT NULL,
                session_id VARCHAR(120) NOT NULL,
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL,
                PRIMARY KEY (account_id, id),
                KEY idx_chats_account_updated (account_id, updated_at),
                CONSTRAINT fk_chats_account
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS messages (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                account_id BIGINT UNSIGNED NOT NULL,
                chat_id VARCHAR(120) NOT NULL,
                speaker VARCHAR(16) NOT NULL,
                text MEDIUMTEXT NOT NULL,
                source VARCHAR(80) NOT NULL DEFAULT '',
                thought_seconds DOUBLE NULL,
                created_at BIGINT NOT NULL,
                PRIMARY KEY (id),
                KEY idx_messages_account_chat_id (account_id, chat_id, id),
                CONSTRAINT fk_messages_chat
                    FOREIGN KEY (account_id, chat_id) REFERENCES chats(account_id, id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS account_events (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                account_id BIGINT UNSIGNED NOT NULL,
                event_type VARCHAR(80) NOT NULL,
                created_at BIGINT NOT NULL,
                PRIMARY KEY (id),
                KEY idx_account_events_account_id (account_id),
                CONSTRAINT fk_account_events_account
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS rate_limit_events (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                identity_key VARCHAR(160) NOT NULL,
                created_at BIGINT NOT NULL,
                PRIMARY KEY (id),
                KEY idx_rate_limit_identity_created (identity_key, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
        ]
        with self._lock, self._connect() as connection:
            with connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)
                cursor.execute("SHOW COLUMNS FROM accounts LIKE 'profile_picture'")
                if cursor.fetchone() is None:
                    cursor.execute(
                        "ALTER TABLE accounts ADD COLUMN profile_picture MEDIUMTEXT NULL AFTER password_hash"
                    )

    def create_account(self, username: str, password: str) -> dict[str, Any]:
        username = _clean_username(username)
        _validate_password(password)
        salt = secrets.token_hex(16)
        password_hash = _hash_password(password, salt)
        now = _now_ms()

        with self._lock, self._connect() as connection:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        """
                        INSERT INTO accounts
                            (username, username_key, password_salt, password_hash, created_at, last_seen_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (username, username.casefold(), salt, password_hash, now, now),
                    )
                except self._pymysql.err.IntegrityError as error:
                    raise AccountError("Account could not be created.") from error

                account_id = int(cursor.lastrowid)
                cursor.execute(
                    "INSERT INTO account_events (account_id, event_type, created_at) VALUES (%s, %s, %s)",
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
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM accounts WHERE username_key = %s", (username.casefold(),))
                row = cursor.fetchone()
                if row is None:
                    raise AuthenticationError("Account could not be authenticated.")

                expected_hash = _hash_password(password, str(row["password_salt"]))
                if not hmac.compare_digest(expected_hash, str(row["password_hash"])):
                    raise AuthenticationError("Account could not be authenticated.")

                account_id = int(row["id"])
                cursor.execute("UPDATE accounts SET last_seen_at = %s WHERE id = %s", (now, account_id))
                cursor.execute(
                    "INSERT INTO account_events (account_id, event_type, created_at) VALUES (%s, %s, %s)",
                    (account_id, "signed_in", now),
                )

        return {
            "id": account_id,
            "username": str(row["username"]),
            "profilePicture": row.get("profile_picture"),
            "createdAt": int(row["created_at"]),
            "lastSeenAt": now,
        }

    def update_profile_picture(self, account_id: int, profile_picture: str | None) -> dict[str, Any]:
        now = _now_ms()
        with self._lock, self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE accounts SET profile_picture = %s, last_seen_at = %s WHERE id = %s",
                    (profile_picture, now, account_id),
                )
                cursor.execute("SELECT * FROM accounts WHERE id = %s", (account_id,))
                row = cursor.fetchone()

        if row is None:
            raise AccountError("Account could not be updated.")
        return {
            "id": int(row["id"]),
            "username": str(row["username"]),
            "profilePicture": row.get("profile_picture"),
            "createdAt": int(row["created_at"]),
            "lastSeenAt": now,
        }

    def create_session(self, account_id: int) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = _hash_token(token)
        now = _now_ms()
        expires_at = now + SESSION_MAX_AGE_SECONDS * 1000

        with self._lock, self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO account_sessions (token_hash, account_id, created_at, expires_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (token_hash, account_id, now, expires_at),
                )

        return token

    def delete_session(self, token: str | None) -> None:
        if not token:
            return
        with self._lock, self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM account_sessions WHERE token_hash = %s", (_hash_token(token),))

    def delete_account(self, account_id: int) -> None:
        with self._lock, self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM accounts WHERE id = %s", (account_id,))

    def get_account_for_session(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None

        now = _now_ms()
        with self._lock, self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM account_sessions WHERE expires_at <= %s", (now,))
                cursor.execute(
                    """
                    SELECT accounts.*
                    FROM account_sessions
                    JOIN accounts ON accounts.id = account_sessions.account_id
                    WHERE account_sessions.token_hash = %s AND account_sessions.expires_at > %s
                    """,
                    (_hash_token(token), now),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                account_id = int(row["id"])
                cursor.execute("UPDATE accounts SET last_seen_at = %s WHERE id = %s", (now, account_id))

        return {
            "id": account_id,
            "username": str(row["username"]),
            "profilePicture": row.get("profile_picture"),
            "createdAt": int(row["created_at"]),
            "lastSeenAt": now,
        }

    def account_stats(self, account_id: int) -> dict[str, int]:
        with self._lock, self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS value FROM chats WHERE account_id = %s", (account_id,))
                chat_count = int(cursor.fetchone()["value"])
                cursor.execute("SELECT COUNT(*) AS value FROM messages WHERE account_id = %s", (account_id,))
                message_count = int(cursor.fetchone()["value"])
                cursor.execute(
                    """
                    SELECT COUNT(*) AS value
                    FROM account_sessions
                    WHERE account_id = %s AND expires_at > %s
                    """,
                    (account_id, _now_ms()),
                )
                session_count = int(cursor.fetchone()["value"])

        return {"chats": chat_count, "messages": message_count, "sessions": session_count}

    def peek_rate_limit(self, identity_key: str) -> dict[str, Any]:
        clean_identity_key = _clean_rate_limit_identity(identity_key)
        with self._lock, self._connect() as connection:
            with connection.cursor() as cursor:
                return self._rate_limit_snapshot(cursor, clean_identity_key, consume=False)

    def consume_rate_limit(self, identity_key: str) -> dict[str, Any]:
        clean_identity_key = _clean_rate_limit_identity(identity_key)
        with self._lock, self._connect() as connection:
            with connection.cursor() as cursor:
                return self._rate_limit_snapshot(cursor, clean_identity_key, consume=True)

    def _rate_limit_snapshot(self, cursor: Any, identity_key: str, *, consume: bool) -> dict[str, Any]:
        now = _now_ms()
        window_start = now - RATE_LIMIT_WINDOW_MS
        cursor.execute("DELETE FROM rate_limit_events WHERE created_at <= %s", (window_start,))
        cursor.execute(
            """
            SELECT created_at
            FROM rate_limit_events
            WHERE identity_key = %s AND created_at > %s
            ORDER BY created_at ASC
            """,
            (identity_key, window_start),
        )
        active_timestamps = [int(row["created_at"]) for row in cursor.fetchall()]

        if len(active_timestamps) >= RATE_LIMIT_LIMIT:
            return _rate_limit_payload(active_timestamps=active_timestamps, now=now, allowed=False)

        if consume:
            cursor.execute(
                "INSERT INTO rate_limit_events (identity_key, created_at) VALUES (%s, %s)",
                (identity_key, now),
            )
            active_timestamps.append(now)

        return _rate_limit_payload(active_timestamps=active_timestamps, now=now, allowed=True)

    def list_chats(self, account_id: int) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, title, session_id, created_at, updated_at
                    FROM chats
                    WHERE account_id = %s
                    ORDER BY updated_at DESC
                    """,
                    (account_id,),
                )
                chat_rows = cursor.fetchall()
                cursor.execute(
                    """
                    SELECT chat_id, speaker, text, source, thought_seconds, created_at
                    FROM messages
                    WHERE account_id = %s
                    ORDER BY id
                    """,
                    (account_id,),
                )
                message_rows = cursor.fetchall()

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
            with connection.cursor() as cursor:
                if incoming_ids:
                    placeholders = ",".join("%s" for _ in incoming_ids)
                    cursor.execute(
                        f"DELETE FROM chats WHERE account_id = %s AND id NOT IN ({placeholders})",
                        (account_id, *incoming_ids),
                    )
                else:
                    cursor.execute("DELETE FROM chats WHERE account_id = %s", (account_id,))

                for chat in clean_chats:
                    cursor.execute(
                        """
                        INSERT INTO chats (id, account_id, title, session_id, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            title = VALUES(title),
                            session_id = VALUES(session_id),
                            updated_at = VALUES(updated_at)
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
                    cursor.execute(
                        "DELETE FROM messages WHERE account_id = %s AND chat_id = %s",
                        (account_id, chat["id"]),
                    )
                    if chat["messages"]:
                        cursor.executemany(
                            """
                            INSERT INTO messages
                                (account_id, chat_id, speaker, text, source, thought_seconds, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
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
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO chats (id, account_id, title, session_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        title = IF(chats.title = 'New chat', VALUES(title), chats.title),
                        session_id = VALUES(session_id),
                        updated_at = VALUES(updated_at)
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
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 AS found FROM chats WHERE id = %s AND account_id = %s",
                    (clean_chat_id, account_id),
                )
                if cursor.fetchone() is None:
                    return
                cursor.execute(
                    """
                    INSERT INTO messages
                        (account_id, chat_id, speaker, text, source, thought_seconds, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
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
                cursor.execute(
                    "UPDATE chats SET updated_at = %s WHERE id = %s AND account_id = %s",
                    (_now_ms(), clean_chat_id, account_id),
                )

    def history_for_chat(self, account_id: int, chat_id: str, max_turns: int = 8) -> ConversationHistory:
        clean_chat_id = _clean_identifier(chat_id, "chat")
        with self._lock, self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT speaker, text
                    FROM messages
                    WHERE account_id = %s AND chat_id = %s
                    ORDER BY id
                    """,
                    (account_id, clean_chat_id),
                )
                rows = cursor.fetchall()

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


def mysql_config_from_env() -> dict[str, Any] | None:
    host = os.environ.get("DB_HOST", "").strip()
    database = os.environ.get("DB_NAME", "").strip()
    username = (
        os.environ.get("DB_USERNAME", "").strip()
        or os.environ.get("DB_USER", "").strip()
    )
    password = os.environ.get("DB_PASSWORD", "")
    if not all((host, database, username, password)):
        return None

    try:
        port = int(os.environ.get("DB_PORT", "3306"))
    except ValueError:
        port = 3306

    return {
        "host": host,
        "port": port,
        "database": database,
        "username": username,
        "password": password,
        "ssl_enabled": os.environ.get("DB_SSL", "").strip().lower() in {"1", "true", "yes"},
    }


def _load_pymysql() -> Any:
    os.environ.setdefault("USER", "learny")
    os.environ.setdefault("USERNAME", "learny")

    for vendor_path in _candidate_vendor_paths():
        if vendor_path.is_dir():
            vendor_text = str(vendor_path)
            if vendor_text not in sys.path:
                sys.path.insert(0, vendor_text)

    try:
        import pymysql
    except ImportError as error:
        raise RuntimeError(
            "Wasmer MySQL storage is configured, but PyMySQL is not installed. "
            "Install dependencies from requirements.txt or include the vendor folder in the package."
        ) from error
    return pymysql


def _candidate_vendor_paths() -> list[Path]:
    project_root = Path(__file__).resolve().parent.parent
    return [Path("/vendor"), Path("/app/vendor"), project_root / "vendor"]
