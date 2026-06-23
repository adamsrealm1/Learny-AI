from __future__ import annotations

import sys
from pathlib import Path


for path in (Path("/"), Path(__file__).resolve().parent.parent):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

from learny.web_server import main


if __name__ == "__main__":
    raise SystemExit(main())
