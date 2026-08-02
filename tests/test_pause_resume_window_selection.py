"""pytest-qt tests for pause/resume control gating on window selection."""

import pytest
from PyQt6.QtWidgets import QMessageBox

from drawing_coach.hotkey_manager import HotkeyManager
from drawing_coach.capture_engine import CaptureEngine
from drawing_coach.main_window import MainWindow
from drawing_coach.window_manager import WindowInfo


@pytest.fixture()
def main_window(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setattr(HotkeyManager, "_start", lambda self: None)
    monkeypatch.setattr(HotkeyManager, "_stop", lambda self: None)
    monkeypatch.setattr(CaptureEngine, "start", lambda self: None)

    win = MainWindow()
    qtbot.addWidget(win)
    yield win
    win._capture.stop()
    win._tray.hide()


def test_pause_button_disabled_at_startup(main_window):
    assert main_window._capture.target is None
    assert not main_window._pause_btn.isEnabled()
    assert not main_window._tray_pause_action.isEnabled()
    assert main_window._pause_btn.text() == "Resume"
    assert main_window._tray_pause_action.text() == "Resume Capture"


def test_pause_button_enabled_after_window_selected(main_window):
    window = WindowInfo(id=1, title="MyCanvas", app_name="Krita")
    main_window._capture.set_target(window)
    main_window._capture.resume()
    main_window._update_status()

    assert main_window._pause_btn.isEnabled()
    assert main_window._tray_pause_action.isEnabled()
    assert main_window._pause_btn.text() == "Pause"


def test_pause_button_disabled_after_window_lost(main_window, monkeypatch):
    window = WindowInfo(id=1, title="MyCanvas", app_name="Krita")
    main_window._capture.set_target(window)
    main_window._capture.resume()
    main_window._update_status()
    assert main_window._pause_btn.isEnabled()

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **kw: None)
    main_window._open_app_selection = lambda: None

    main_window._on_window_lost()

    assert not main_window._pause_btn.isEnabled()
    assert not main_window._tray_pause_action.isEnabled()
    assert main_window._pause_btn.text() == "Resume"
