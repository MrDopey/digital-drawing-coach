"""pytest-qt tests for the system tray icon's context menu and restore behavior."""

import pytest
from PyQt6.QtWidgets import QSystemTrayIcon

from drawing_coach.hotkey_manager import HotkeyManager
from drawing_coach.capture_engine import CaptureEngine
from drawing_coach.main_window import MainWindow


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


def _menu_action_texts(main_window):
    return [a.text() for a in main_window._tray.contextMenu().actions()]


def test_tray_menu_top_item_is_show_drawing_coach(main_window):
    actions = main_window._tray.contextMenu().actions()
    assert actions[0].text() == "Show Drawing Coach"


def test_tray_menu_excludes_removed_shortcuts(main_window):
    texts = _menu_action_texts(main_window)
    assert "Get Feedback" not in texts
    assert "Memory" not in texts
    assert "Progress" not in texts


def test_restore_shows_raises_and_activates_hidden_window(main_window):
    main_window.hide()
    assert not main_window.isVisible()

    main_window._restore_main_window()

    assert main_window.isVisible()


def test_restore_is_safe_when_already_visible(main_window):
    main_window.show()
    assert main_window.isVisible()

    main_window._restore_main_window()

    assert main_window.isVisible()


def test_double_click_restores_window(main_window):
    main_window.hide()

    main_window._on_tray_activated(QSystemTrayIcon.ActivationReason.DoubleClick)

    assert main_window.isVisible()


@pytest.mark.parametrize(
    "reason",
    [
        QSystemTrayIcon.ActivationReason.Trigger,
        QSystemTrayIcon.ActivationReason.MiddleClick,
    ],
)
def test_non_double_click_reasons_do_not_restore_window(main_window, reason):
    main_window.hide()

    main_window._on_tray_activated(reason)

    assert not main_window.isVisible()
