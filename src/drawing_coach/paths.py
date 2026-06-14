from __future__ import annotations

import os
import sys
from pathlib import Path

_APP = "drawing-coach"


def _xdg(var: str, fallback: str) -> Path:
    val = os.environ.get(var, "").strip()
    return Path(val) if val else Path.home() / fallback


def config_path() -> Path:
    if sys.platform == "win32":
        return Path.home() / f".{_APP}" / "config.json"
    return _xdg("XDG_CONFIG_HOME", ".config") / _APP / "config.json"


def sessions_dir() -> Path:
    if sys.platform == "win32":
        return Path.home() / f".{_APP}" / "sessions"
    return _xdg("XDG_DATA_HOME", ".local/share") / _APP / "sessions"
