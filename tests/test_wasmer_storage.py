from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from learny.database import LearnyDatabase
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


if __name__ == "__main__":
    unittest.main()
