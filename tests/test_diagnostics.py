"""Tests for drawing_coach.diagnostics check functions and DiagnosticsDialog."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication

from drawing_coach.diagnostics import (
    CheckResult,
    DiagnosticsDialog,
    check_config_path,
    check_input_monitoring,
    check_llm,
    check_pillow_png,
    check_screen_capture,
    check_sessions_dir,
    check_xdotool,
)
from drawing_coach.llm_config import LLMConfig


# ---------------------------------------------------------------------------
# macOS backend helpers (task 1.3)
# ---------------------------------------------------------------------------


def test_has_screen_recording_permission_true():
    mock_quartz = MagicMock()
    mock_quartz.CGWindowListCopyWindowInfo.return_value = [{"kCGWindowName": "Finder"}]
    mock_quartz.kCGWindowListOptionAll = 0
    mock_quartz.kCGNullWindowID = 0
    with patch.dict("sys.modules", {"Quartz": mock_quartz}):
        from drawing_coach._backend_macos import has_screen_recording_permission

        assert has_screen_recording_permission() is True


def test_has_screen_recording_permission_false():
    mock_quartz = MagicMock()
    mock_quartz.CGWindowListCopyWindowInfo.return_value = []
    mock_quartz.kCGWindowListOptionAll = 0
    mock_quartz.kCGNullWindowID = 0
    with patch.dict("sys.modules", {"Quartz": mock_quartz}):
        from drawing_coach._backend_macos import has_screen_recording_permission

        assert has_screen_recording_permission() is False


def test_has_input_monitoring_permission_true():
    mock_lib = MagicMock()
    mock_lib.AXIsProcessTrustedWithOptions.return_value = True
    with (
        patch("ctypes.util.find_library", return_value="/lib/ApplicationServices"),
        patch("ctypes.cdll.LoadLibrary", return_value=mock_lib),
    ):
        from drawing_coach._backend_macos import has_input_monitoring_permission

        assert has_input_monitoring_permission() is True


def test_has_input_monitoring_permission_false():
    mock_lib = MagicMock()
    mock_lib.AXIsProcessTrustedWithOptions.return_value = False
    with (
        patch("ctypes.util.find_library", return_value="/lib/ApplicationServices"),
        patch("ctypes.cdll.LoadLibrary", return_value=mock_lib),
    ):
        from drawing_coach._backend_macos import has_input_monitoring_permission

        assert has_input_monitoring_permission() is False


# ---------------------------------------------------------------------------
# check_screen_capture
# ---------------------------------------------------------------------------


def test_check_screen_capture_linux_pass(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    mock_mss = MagicMock()
    mock_sct = MagicMock()
    mock_mss.mss.return_value.__enter__ = lambda s: mock_sct
    mock_mss.mss.return_value.__exit__ = MagicMock(return_value=False)
    mock_sct.monitors = [{"top": 0, "left": 0, "width": 1920, "height": 1080}]
    with patch.dict("sys.modules", {"mss": mock_mss}):
        result = check_screen_capture()
    assert result.passed
    assert "available" in result.message


def test_check_screen_capture_linux_fail(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    mock_mss = MagicMock()
    mock_mss.mss.return_value.__enter__ = MagicMock(side_effect=OSError("no display"))
    mock_mss.mss.return_value.__exit__ = MagicMock(return_value=False)
    with patch.dict("sys.modules", {"mss": mock_mss}):
        result = check_screen_capture()
    assert not result.passed
    assert result.hint


def test_check_screen_capture_macos_granted(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    with patch(
        "drawing_coach.diagnostics.check_screen_capture.__wrapped__"
        if hasattr(check_screen_capture, "__wrapped__") else
        "drawing_coach._backend_macos.has_screen_recording_permission",
        return_value=True,
        create=True,
    ):
        with patch(
            "drawing_coach.diagnostics.sys.platform", "darwin"
        ), patch(
            "drawing_coach._backend_macos.has_screen_recording_permission",
            return_value=True,
        ):
            result = check_screen_capture()
    assert result.passed
    assert "granted" in result.message


def test_check_screen_capture_macos_denied(monkeypatch):
    with patch("drawing_coach.diagnostics.sys.platform", "darwin"), patch(
        "drawing_coach._backend_macos.has_screen_recording_permission",
        return_value=False,
    ):
        result = check_screen_capture()
    assert not result.passed
    assert "denied" in result.message
    assert result.hint


# ---------------------------------------------------------------------------
# check_input_monitoring
# ---------------------------------------------------------------------------


def test_check_input_monitoring_granted():
    with patch("drawing_coach.diagnostics.sys.platform", "darwin"), patch(
        "drawing_coach._backend_macos.has_input_monitoring_permission",
        return_value=True,
    ):
        result = check_input_monitoring()
    assert result.passed
    assert "granted" in result.message


def test_check_input_monitoring_denied():
    with patch("drawing_coach.diagnostics.sys.platform", "darwin"), patch(
        "drawing_coach._backend_macos.has_input_monitoring_permission",
        return_value=False,
    ):
        result = check_input_monitoring()
    assert not result.passed
    assert result.hint


# ---------------------------------------------------------------------------
# check_xdotool
# ---------------------------------------------------------------------------


def test_check_xdotool_found():
    with patch("shutil.which", return_value="/usr/bin/xdotool"):
        result = check_xdotool()
    assert result.passed
    assert "found" in result.message


def test_check_xdotool_missing():
    with patch("shutil.which", return_value=None):
        result = check_xdotool()
    assert not result.passed
    assert result.hint


# ---------------------------------------------------------------------------
# check_llm
# ---------------------------------------------------------------------------


def test_check_llm_no_model():
    result = check_llm(LLMConfig())
    assert not result.passed
    assert "No model" in result.message
    assert result.hint


def test_check_llm_success():
    cfg = LLMConfig(model="gpt-4o")
    with patch("litellm.completion", return_value=MagicMock()):
        result = check_llm(cfg)
    assert result.passed
    assert "successful" in result.message


def test_check_llm_failure():
    cfg = LLMConfig(model="gpt-4o")
    with patch("litellm.completion", side_effect=Exception("AuthenticationError")):
        result = check_llm(cfg)
    assert not result.passed
    assert "AuthenticationError" in result.message
    assert result.hint


# ---------------------------------------------------------------------------
# check_config_path
# ---------------------------------------------------------------------------


def test_check_config_path_writable(tmp_path):
    p = tmp_path / "config.json"
    with patch("drawing_coach.diagnostics.config_path", return_value=p):
        result = check_config_path()
    assert result.passed
    assert str(p) in result.message


def test_check_config_path_not_writable(tmp_path):
    p = tmp_path / "config.json"
    with (
        patch("drawing_coach.diagnostics.config_path", return_value=p),
        patch("os.access", return_value=False),
    ):
        result = check_config_path()
    assert not result.passed
    assert result.hint


def test_check_config_path_corrupt_json(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{not valid json")
    with patch("drawing_coach.diagnostics.config_path", return_value=p):
        result = check_config_path()
    assert not result.passed
    assert "corrupt" in result.message
    assert result.hint


def test_check_config_path_valid_json(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"model": "gpt-4o"}))
    with patch("drawing_coach.diagnostics.config_path", return_value=p):
        result = check_config_path()
    assert result.passed


# ---------------------------------------------------------------------------
# check_sessions_dir
# ---------------------------------------------------------------------------


def test_check_sessions_dir_writable(tmp_path):
    d = tmp_path / "sessions"
    with patch("drawing_coach.diagnostics.sessions_dir", return_value=d):
        result = check_sessions_dir()
    assert result.passed
    assert str(d) in result.message
    assert not (d / ".diag_probe").exists()


def test_check_sessions_dir_not_creatable(tmp_path):
    d = tmp_path / "sessions"
    with (
        patch("drawing_coach.diagnostics.sessions_dir", return_value=d),
        patch("pathlib.Path.mkdir", side_effect=OSError("permission denied")),
    ):
        result = check_sessions_dir()
    assert not result.passed
    assert result.hint


def test_check_sessions_dir_not_writable(tmp_path):
    d = tmp_path / "sessions"
    d.mkdir()
    with (
        patch("drawing_coach.diagnostics.sessions_dir", return_value=d),
        patch("pathlib.Path.write_text", side_effect=OSError("read-only")),
    ):
        result = check_sessions_dir()
    assert not result.passed
    assert result.hint


# ---------------------------------------------------------------------------
# check_pillow_png
# ---------------------------------------------------------------------------


def test_check_pillow_png_pass():
    result = check_pillow_png()
    assert result.passed
    assert "available" in result.message


def test_check_pillow_png_fail():
    mock_image_cls = MagicMock()
    mock_image_cls.new.return_value.save.side_effect = Exception("codec missing")
    with patch.dict("sys.modules", {"PIL": MagicMock(), "PIL.Image": mock_image_cls}):
        with patch("drawing_coach.diagnostics.check_pillow_png.__module__"):
            pass
    # Patch at the point of use inside the function
    with patch("PIL.Image.new") as mock_new:
        mock_new.return_value.save.side_effect = Exception("codec missing")
        result = check_pillow_png()
    assert not result.passed
    assert result.hint


# ---------------------------------------------------------------------------
# DiagnosticsDialog — pytest-qt (task 5.2)
# ---------------------------------------------------------------------------


def _noop_checks(config: LLMConfig):
    return [
        ("Screen Capture", lambda: CheckResult("Screen Capture", True, "ok")),
        ("LLM Connection", lambda: CheckResult("LLM Connection", True, "ok")),
        ("Config Access", lambda: CheckResult("Config Access", True, "ok")),
        ("Sessions Directory", lambda: CheckResult("Sessions Directory", True, "ok")),
        ("Pillow PNG", lambda: CheckResult("Pillow PNG", True, "ok")),
    ]


def test_dialog_all_pass(qtbot):
    cfg = LLMConfig(model="gpt-4o")
    with patch("drawing_coach.diagnostics.build_checks", side_effect=_noop_checks):
        dlg = DiagnosticsDialog(config=cfg)
        qtbot.addWidget(dlg)
        qtbot.waitSignal(dlg._coordinator.all_done, timeout=5000)
        qtbot.wait(200)  # allow queued check_done signals to be processed

    for name, status_lbl in dlg._status_labels.items():
        assert status_lbl.text() == "✓", f"{name} did not show ✓"


# ---------------------------------------------------------------------------
# DiagnosticsDialog — LLM failure row (task 5.3)
# ---------------------------------------------------------------------------


def _llm_fail_checks(config: LLMConfig):
    return [
        ("Screen Capture", lambda: CheckResult("Screen Capture", True, "ok")),
        (
            "LLM Connection",
            lambda: CheckResult(
                "LLM Connection", False, "AuthenticationError: bad key", hint="Check your API key"
            ),
        ),
    ]


def test_dialog_llm_fail_row(qtbot):
    cfg = LLMConfig(model="gpt-4o")
    with patch("drawing_coach.diagnostics.build_checks", side_effect=_llm_fail_checks):
        dlg = DiagnosticsDialog(config=cfg)
        qtbot.addWidget(dlg)
        qtbot.waitSignal(dlg._coordinator.all_done, timeout=5000)
        qtbot.wait(200)  # allow queued check_done signals to be processed

    assert dlg._status_labels["LLM Connection"].text() == "✗"
    msg = dlg._msg_labels["LLM Connection"].text()
    assert "AuthenticationError" in msg
    hint = dlg._hint_labels["LLM Connection"].text()
    assert "Check your API key" in hint
