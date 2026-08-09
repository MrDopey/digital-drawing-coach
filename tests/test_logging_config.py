"""Tests for logging bootstrap (logging_config.setup_logging)."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from unittest.mock import patch

import pytest

import drawing_coach.logging_config  # ensure module is importable before patching
from drawing_coach import perf
from drawing_coach.logging_config import setup_logging


def _reset_logger() -> None:
    root = logging.getLogger("drawing_coach")
    for h in list(root.handlers):
        h.close()
        root.removeHandler(h)
    root.setLevel(logging.NOTSET)


def _call_setup(
    monkeypatch, *, level="", log_file="", max_bytes="", watchdog="", stall_ms=""
) -> None:
    monkeypatch.setenv("DRAWING_COACH_LOG_LEVEL", level)
    monkeypatch.setenv("DRAWING_COACH_LOG_FILE", log_file)
    monkeypatch.setenv("DRAWING_COACH_LOG_MAX_BYTES", max_bytes)
    monkeypatch.setenv("DRAWING_COACH_PERF_WATCHDOG", watchdog)
    monkeypatch.setenv("DRAWING_COACH_PERF_STALL_MS", stall_ms)
    with patch("dotenv.load_dotenv"):
        setup_logging()


def test_valid_level_info(monkeypatch):
    _reset_logger()
    _call_setup(monkeypatch, level="INFO")
    assert logging.getLogger("drawing_coach").level == logging.INFO
    _reset_logger()


def test_valid_level_debug(monkeypatch):
    _reset_logger()
    _call_setup(monkeypatch, level="DEBUG")
    assert logging.getLogger("drawing_coach").level == logging.DEBUG
    _reset_logger()


def test_level_case_insensitive(monkeypatch):
    _reset_logger()
    _call_setup(monkeypatch, level="warning")
    assert logging.getLogger("drawing_coach").level == logging.WARNING
    _reset_logger()


def test_invalid_level_defaults_to_warning(monkeypatch, capsys):
    _reset_logger()
    _call_setup(monkeypatch, level="VERBOSE")
    assert logging.getLogger("drawing_coach").level == logging.WARNING
    captured = capsys.readouterr()
    assert "VERBOSE" in captured.err
    assert "WARNING" in captured.err
    _reset_logger()


def test_unset_level_defaults_to_warning(monkeypatch):
    _reset_logger()
    _call_setup(monkeypatch)
    assert logging.getLogger("drawing_coach").level == logging.WARNING
    _reset_logger()


def test_no_file_handler_when_log_file_unset(monkeypatch):
    _reset_logger()
    _call_setup(monkeypatch)
    root = logging.getLogger("drawing_coach")
    assert not any(isinstance(h, RotatingFileHandler) for h in root.handlers)
    _reset_logger()


def test_rotating_file_handler_added_when_log_file_set(monkeypatch, tmp_path):
    _reset_logger()
    log_path = tmp_path / "app.log"
    _call_setup(monkeypatch, log_file=str(log_path))
    root = logging.getLogger("drawing_coach")
    fh = next((h for h in root.handlers if isinstance(h, RotatingFileHandler)), None)
    assert fh is not None
    assert fh.maxBytes == 10 * 1024 * 1024
    assert fh.backupCount == 0
    _reset_logger()


def test_custom_max_bytes_respected(monkeypatch, tmp_path):
    _reset_logger()
    log_path = tmp_path / "app.log"
    _call_setup(monkeypatch, log_file=str(log_path), max_bytes="5242880")
    root = logging.getLogger("drawing_coach")
    fh = next((h for h in root.handlers if isinstance(h, RotatingFileHandler)), None)
    assert fh is not None
    assert fh.maxBytes == 5242880
    _reset_logger()


def test_missing_log_file_parent_skips_file_handler(monkeypatch, tmp_path, capsys):
    _reset_logger()
    bad_path = tmp_path / "nonexistent_dir" / "app.log"
    _call_setup(monkeypatch, log_file=str(bad_path))
    root = logging.getLogger("drawing_coach")
    assert not any(isinstance(h, RotatingFileHandler) for h in root.handlers)
    captured = capsys.readouterr()
    assert "Cannot write log file" in captured.err
    _reset_logger()


def test_invalid_max_bytes_defaults_to_10mb(monkeypatch, tmp_path, capsys):
    _reset_logger()
    log_path = tmp_path / "app.log"
    _call_setup(monkeypatch, log_file=str(log_path), max_bytes="abc")
    root = logging.getLogger("drawing_coach")
    fh = next((h for h in root.handlers if isinstance(h, RotatingFileHandler)), None)
    assert fh is not None
    assert fh.maxBytes == 10 * 1024 * 1024
    captured = capsys.readouterr()
    assert "abc" in captured.err
    _reset_logger()


def test_zero_max_bytes_defaults_to_10mb(monkeypatch, tmp_path, capsys):
    _reset_logger()
    log_path = tmp_path / "app.log"
    _call_setup(monkeypatch, log_file=str(log_path), max_bytes="0")
    root = logging.getLogger("drawing_coach")
    fh = next((h for h in root.handlers if isinstance(h, RotatingFileHandler)), None)
    assert fh is not None
    assert fh.maxBytes == 10 * 1024 * 1024
    _reset_logger()


# ---------------------------------------------------------------------------
# Perf instrumentation wiring
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_perf():
    perf.reset_for_tests()
    logging.getLogger("drawing_coach.perf").setLevel(logging.NOTSET)
    yield
    perf.reset_for_tests()
    logging.getLogger("drawing_coach.perf").setLevel(logging.NOTSET)


def test_perf_disabled_by_default_changes_nothing(monkeypatch, tmp_path):
    _reset_logger()
    _call_setup(monkeypatch, log_file=str(tmp_path / "app.log"))
    assert perf.ON is False
    assert logging.getLogger("drawing_coach.perf").level == logging.NOTSET
    _reset_logger()


def test_perf_logger_is_debug_while_root_stays_warning(monkeypatch, tmp_path):
    # The carve-out: perf records flow through the existing handlers without
    # making litellm/urllib3 or anything else noisier.
    _reset_logger()
    _call_setup(
        monkeypatch, log_file=str(tmp_path / "app.log"), watchdog="1"
    )
    assert logging.getLogger("drawing_coach").level == logging.WARNING
    assert logging.getLogger("drawing_coach.perf").level == logging.DEBUG
    _reset_logger()


def test_perf_creates_a_log_file_when_none_is_configured(monkeypatch, tmp_path):
    _reset_logger()
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _call_setup(monkeypatch, watchdog="1")
    root = logging.getLogger("drawing_coach")
    handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
    assert len(handlers) == 1
    expected = tmp_path / "drawing-coach" / "debug_logs" / "perf.log"
    assert handlers[0].baseFilename == str(expected)
    _reset_logger()


def test_perf_reuses_the_configured_log_file(monkeypatch, tmp_path):
    _reset_logger()
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    log_path = tmp_path / "app.log"
    _call_setup(monkeypatch, log_file=str(log_path), watchdog="1")
    root = logging.getLogger("drawing_coach")
    handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
    assert len(handlers) == 1  # no second, perf-specific file
    assert handlers[0].baseFilename == str(log_path)
    _reset_logger()


def test_perf_auto_log_file_honours_the_size_cap(monkeypatch, tmp_path):
    _reset_logger()
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _call_setup(monkeypatch, watchdog="1", max_bytes="5242880")
    root = logging.getLogger("drawing_coach")
    fh = next(h for h in root.handlers if isinstance(h, RotatingFileHandler))
    assert fh.maxBytes == 5242880
    _reset_logger()


def test_perf_stall_threshold_is_applied(monkeypatch, tmp_path):
    _reset_logger()
    _call_setup(
        monkeypatch,
        log_file=str(tmp_path / "app.log"),
        watchdog="1",
        stall_ms="500",
    )
    assert perf.stall_threshold_ms() == 500.0
    _reset_logger()


def test_perf_full_mode_sets_both_flags(monkeypatch, tmp_path):
    _reset_logger()
    _call_setup(monkeypatch, log_file=str(tmp_path / "app.log"), watchdog="full")
    assert perf.ON is True
    assert perf.FULL is True
    _reset_logger()


def test_disabled_instrumentation_creates_no_machinery(monkeypatch, tmp_path):
    """The cost-when-off guarantee, asserted rather than assumed.

    Instrumentation that quietly costs something would be a performance bug of
    exactly the kind it exists to find.
    """
    import gc
    import threading

    _reset_logger()
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    before = {t.name for t in threading.enumerate()}

    _call_setup(monkeypatch)  # watchdog unset
    assert perf.install_watchdog() is None

    root = logging.getLogger("drawing_coach")
    assert perf.ON is False
    assert perf._watchdog is None                      # no watchdog thread
    assert perf._heartbeat is None                     # no heartbeat QTimer
    assert perf._on_gc not in gc.callbacks             # no GC callback
    assert not any(                                    # no perf log handler
        isinstance(h, RotatingFileHandler) for h in root.handlers
    )
    assert not (tmp_path / "drawing-coach" / "debug_logs").exists()
    assert {t.name for t in threading.enumerate()} - before == set()
    _reset_logger()
