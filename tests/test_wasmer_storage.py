from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from learny.database import LearnyDatabase, _rate_limit_window
from learny.mysql_database import mysql_config_from_env
from learny.storage import create_learny_database


class WasmerStorageTests(unittest.TestCase):
    def test_app_yaml_requests_wasmer_mysql_database(self) -> None:
        app_yaml = Path("app.yaml").read_text(encoding="utf-8")

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

    def test_rate_limit_global_reset_keeps_only_current_window_events(self) -> None:
        now = 1_781_625_600_000
        window_start, reset_at, _window_ms = _rate_limit_window(now)

        with TemporaryDirectory() as temp_dir:
            database = LearnyDatabase(Path(temp_dir) / "learny.sqlite3")
            with database._connect() as connection:
                connection.executemany(
                    "INSERT INTO rate_limit_events (identity_key, created_at) VALUES (?, ?)",
                    [
                        ("global:signed-in", window_start - 10_000),
                        ("global:signed-in", reset_at + 10_000),
                        ("global:signed-in", window_start + 10_000),
                        ("global:guest", window_start - 5_000),
                    ],
                )

            with patch("learny.database._now_ms", return_value=now):
                signed_in_limit = database.peek_rate_limit("global:signed-in", limit=200)
                guest_limit = database.peek_rate_limit("global:guest", limit=30)

            with database._connect() as connection:
                rows = connection.execute(
                    "SELECT identity_key, created_at FROM rate_limit_events ORDER BY created_at"
                ).fetchall()

        self.assertEqual(signed_in_limit["remaining"], 199)
        self.assertEqual(guest_limit["remaining"], 30)
        self.assertEqual(
            [(row["identity_key"], row["created_at"]) for row in rows],
            [("global:signed-in", window_start + 10_000)],
        )


if __name__ == "__main__":
    unittest.main()
