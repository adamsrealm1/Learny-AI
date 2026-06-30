from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


DEFAULT_URL = "https://learny.env.pm"
DEFAULT_WIDTH = 2000
DEFAULT_HEIGHT = 1000
MIN_WIDTH = 1200
MIN_HEIGHT = 700
APP_USER_MODEL_ID = "LearnyAI.Desktop"
DATA_FOLDER_NAME = "Learny AI"
ICON_FILE_NAME = "Learny.ico"


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundled_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", app_root())).resolve()


def appdata_root() -> Path:
    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        return Path(appdata)
    return Path.home() / "AppData" / "Roaming"


def find_original_icon() -> Path | None:
    candidates = (
        app_root() / "logos" / ICON_FILE_NAME,
        bundled_root() / "logos" / ICON_FILE_NAME,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def prepare_runtime_data() -> dict[str, Path | None]:
    data_dir = appdata_root() / DATA_FOLDER_NAME
    storage_dir = data_dir / "storage"
    cookies_dir = data_dir / "cookies"
    fallback_icon = data_dir / ICON_FILE_NAME

    storage_dir.mkdir(parents=True, exist_ok=True)
    cookies_dir.mkdir(parents=True, exist_ok=True)

    original_icon = find_original_icon()
    if original_icon is not None:
        try:
            if not fallback_icon.exists() or original_icon.stat().st_size != fallback_icon.stat().st_size:
                shutil.copy2(original_icon, fallback_icon)
        except OSError:
            pass

    icon_path = original_icon if original_icon is not None else fallback_icon if fallback_icon.is_file() else None
    return {
        "data_dir": data_dir,
        "storage_dir": storage_dir,
        "cookies_dir": cookies_dir,
        "icon_path": icon_path,
    }


def enable_windows_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open Learny AI in a desktop window.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"Website URL to open. Defaults to {DEFAULT_URL}.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=DEFAULT_WIDTH,
        help=f"Initial window width. Defaults to {DEFAULT_WIDTH}.",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=DEFAULT_HEIGHT,
        help=f"Initial window height. Defaults to {DEFAULT_HEIGHT}.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Open the webview with debug tools enabled.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runtime_paths = prepare_runtime_data()
    enable_windows_dpi_awareness()

    try:
        import webview
    except ImportError:
        print(
            "Missing dependency: pywebview\n\n"
            "Install it with:\n"
            "  python -m pip install pywebview\n\n"
            "Then run:\n"
            "  python LearnyAI_desktop.py",
            file=sys.stderr,
        )
        return 1

    webview.create_window(
        "Learny AI - One Smart AI",
        args.url,
        width=max(args.width, MIN_WIDTH),
        height=max(args.height, MIN_HEIGHT),
        min_size=(MIN_WIDTH, MIN_HEIGHT),
    )

    start_options = {
        "debug": args.debug,
        "private_mode": False,
        "storage_path": str(runtime_paths["storage_dir"]),
    }
    if runtime_paths["icon_path"] is not None:
        start_options["icon"] = str(runtime_paths["icon_path"])

    webview.start(**start_options)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
