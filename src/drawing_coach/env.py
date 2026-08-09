"""XDG path helpers and operational environment variable readers."""

from __future__ import annotations

import os


def xdg_config_home() -> str:
    return os.environ.get("XDG_CONFIG_HOME", "").strip()


def xdg_data_home() -> str:
    return os.environ.get("XDG_DATA_HOME", "").strip()


def log_level() -> str:
    return os.environ.get("DRAWING_COACH_LOG_LEVEL", "").strip()


def log_file() -> str:
    return os.environ.get("DRAWING_COACH_LOG_FILE", "").strip()


def log_max_bytes() -> str:
    return os.environ.get("DRAWING_COACH_LOG_MAX_BYTES", "").strip()


def perf_watchdog() -> str:
    return os.environ.get("DRAWING_COACH_PERF_WATCHDOG", "").strip()


def perf_stall_ms() -> str:
    return os.environ.get("DRAWING_COACH_PERF_STALL_MS", "").strip()
