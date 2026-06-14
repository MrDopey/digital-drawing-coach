"""Single location for all os.environ reads and writes in the application."""

from __future__ import annotations

import os


def xdg_config_home() -> str:
    return os.environ.get("XDG_CONFIG_HOME", "").strip()


def xdg_data_home() -> str:
    return os.environ.get("XDG_DATA_HOME", "").strip()


def api_key() -> str:
    return os.environ.get("DRAWING_COACH_API_KEY", "")


def set_api_key(value: str) -> None:
    if value:
        os.environ["DRAWING_COACH_API_KEY"] = value
    else:
        os.environ.pop("DRAWING_COACH_API_KEY", None)


def model() -> str:
    return os.environ.get("DRAWING_COACH_MODEL", "")


def api_base() -> str:
    return os.environ.get("DRAWING_COACH_API_BASE", "")


def log_level() -> str:
    return os.environ.get("DRAWING_COACH_LOG_LEVEL", "").strip()


def log_file() -> str:
    return os.environ.get("DRAWING_COACH_LOG_FILE", "").strip()


def log_max_bytes() -> str:
    return os.environ.get("DRAWING_COACH_LOG_MAX_BYTES", "").strip()
