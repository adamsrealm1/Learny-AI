from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from learny.database import LearnyDatabase, _rate_limit_window
from learny.mysql_database import mysql_config_from_env
from learny.storage import create_learny_database


APP_ROOT = Path(__file__).resolve().parents[1]


class WasmerStorageTests(unittest.TestCase):
    def test_app_yaml_requests_wasmer_mysql_database(self) -> None:
        app_yaml = (APP_ROOT / "app.yaml").read_text(encoding="utf-8")

        self.assertIn("capabilities:", app_yaml)
        self.assertIn("database:", app_yaml)
        self.assertIn("engine: mysql", app_yaml)
        self.assertIn("locality:", app_yaml)
        self.assertIn("us-socal1", app_yaml)

    def test_mysql_config_reads_wasmer_database_environment(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DB_HOST": "mysql.internal",
                "DB_PORT": "3307",
                "DB_NAME": "learny",
                "DB_USERNAME": "learny_user",
                "DB_PASSWORD": "secret",
            },
            clear=True,
        ):
            config = mysql_config_from_env()

        assert config is not None
        self.assertEqual(config["host"], "mysql.internal")
        self.assertEqual(config["port"], 3307)
        self.assertEqual(config["database"], "learny")
        self.assertEqual(config["username"], "learny_user")
        self.assertEqual(config["password"], "secret")

    def test_mysql_config_accepts_db_user_alias(self) -> None:
        with patch.dict(
            os.environ,
            {
                "DB_HOST": "mysql.internal",
                "DB_NAME": "learny",
                "DB_USER": "legacy_user",
                "DB_PASSWORD": "secret",
            },
            clear=True,
        ):
            config = mysql_config_from_env()

        assert config is not None
        self.assertEqual(config["port"], 3306)
        self.assertEqual(config["username"], "legacy_user")

    def test_explicit_sqlite_path_keeps_local_tests_on_sqlite(self) -> None:
        with TemporaryDirectory() as temp_dir:
            with patch.dict(os.environ, {}, clear=True):
                database = create_learny_database(
                    Path(temp_dir) / "learny.sqlite3",
                    prefer_wasmer_database=False,
                )

        self.assertIsInstance(database, LearnyDatabase)
        self.assertEqual(database.backend_name, "sqlite")

    def test_rate_limit_window_uses_requested_local_midnight(self) -> None:
        now = int(datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc).timestamp() * 1000)
        _window_start, reset_at, window_ms = _rate_limit_window(now, "Australia/Sydney")
        expected_reset_at = int(datetime(2026, 6, 28, 14, 0, tzinfo=timezone.utc).timestamp() * 1000)

        self.assertEqual(reset_at, expected_reset_at)
        self.assertEqual(window_ms, 86_400_000)

    def test_rate_limit_window_handles_daylight_saving_midnight(self) -> None:
        now = int(datetime(2026, 3, 8, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)
        _window_start, reset_at, window_ms = _rate_limit_window(now, "America/New_York")
        expected_reset_at = int(datetime(2026, 3, 9, 4, 0, tzinfo=timezone.utc).timestamp() * 1000)

        self.assertEqual(reset_at, expected_reset_at)
        self.assertEqual(window_ms, 82_800_000)

    def test_rate_limit_local_reset_keeps_only_current_identity_window_events(self) -> None:
        now = 1_781_625_600_000
        window_start, reset_at, _window_ms = _rate_limit_window(now, "Australia/Sydney")

        with TemporaryDirectory() as temp_dir:
            database = LearnyDatabase(Path(temp_dir) / "learny.sqlite3")
            with database._connect() as connection:
                connection.executemany(
                    "INSERT INTO rate_limit_events (identity_key, created_at) VALUES (?, ?)",
                    [
                        ("account:1", window_start - 10_000),
                        ("account:1", reset_at + 10_000),
                        ("account:1", window_start + 10_000),
                        ("session:guest", window_start - 5_000),
                        ("account:2", window_start - 10_000),
                    ],
                )

            with patch("learny.database._now_ms", return_value=now):
                signed_in_limit = database.peek_rate_limit(
                    "account:1",
                    limit=200,
                    time_zone="Australia/Sydney",
                )
                guest_limit = database.peek_rate_limit(
                    "session:guest",
                    limit=30,
                    time_zone="Australia/Sydney",
                )

            with database._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT identity_key, created_at
                    FROM rate_limit_events
                    ORDER BY identity_key, created_at
                    """
                ).fetchall()

        self.assertEqual(signed_in_limit["remaining"], 199)
        self.assertEqual(guest_limit["remaining"], 30)
        self.assertEqual(
            [(row["identity_key"], row["created_at"]) for row in rows],
            [
                ("account:1", window_start + 10_000),
                ("account:2", window_start - 10_000),
            ],
        )


if __name__ == "__main__":
    unittest.main()
