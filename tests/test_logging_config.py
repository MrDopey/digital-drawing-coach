"""Tests for logging bootstrap (logging_config.setup_logging)."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from unittest.mock import patch

import drawing_coach.logging_config  # ensure module is importable before patching
from drawing_coach.logging_config import setup_logging


def _reset_logger() -> None:
    root = logging.getLogger("drawing_coach")
    for h in list(root.handlers):
        h.close()
        root.removeHandler(h)
    root.setLevel(logging.NOTSET)


def _call_setup(monkeypatch, *, level="", log_file="", max_bytes="") -> None:
    monkeypatch.setenv("DRAWING_COACH_LOG_LEVEL", level)
    monkeypatch.setenv("DRAWING_COACH_LOG_FILE", log_file)
    monkeypatch.setenv("DRAWING_COACH_LOG_MAX_BYTES", max_bytes)
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
