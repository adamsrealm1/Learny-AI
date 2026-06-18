from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .database import LearnyDatabase
from .mysql_database import MySQLLearnyDatabase, mysql_config_from_env


def create_learny_database(sqlite_path: Path, *, prefer_wasmer_database: bool) -> Any:
    if prefer_wasmer_database and mysql_config_from_env() is not None:
        return MySQLLearnyDatabase.from_env()
    if os.environ.get("LEARNY_DATABASE_BACKEND", "").strip().lower() == "mysql":
        return MySQLLearnyDatabase.from_env()
    return LearnyDatabase(sqlite_path)

