from __future__ import annotations

import sys
from pathlib import Path

from drawing_coach import env

_APP = "drawing-coach"


def config_path() -> Path:
    if sys.platform == "win32":
        return Path.home() / f".{_APP}" / "config.json"
    val = env.xdg_config_home()
    return (Path(val) if val else Path.home() / ".config") / _APP / "config.json"


def sessions_dir() -> Path:
    if sys.platform == "win32":
        return Path.home() / f".{_APP}" / "sessions"
    val = env.xdg_data_home()
    return (Path(val) if val else Path.home() / ".local/share") / _APP / "sessions"


def memory_path() -> Path:
    return sessions_dir().parent / "memory.json"


def memory_summaries_path() -> Path:
    return sessions_dir().parent / "memory_summaries.json"
