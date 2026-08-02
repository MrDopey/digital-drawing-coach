"""Tests for HistoryPanel list layout, ordering, delete buttons, and open-image behaviour."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QColor, QMouseEvent, QPalette
from PyQt6.QtWidgets import QApplication

from drawing_coach.capture_engine import CapturedFrame, CaptureEngine
from drawing_coach.history_panel import HistoryPanel
from drawing_coach.llm_config import LLMConfig
from drawing_coach.theme import Theme
from drawing_coach.window_manager import WindowInfo


def _frame(ts: str, path: Path | None = None) -> CapturedFrame:
    img = Image.new("RGB", (10, 10), (100, 100, 100))
    return CapturedFrame(image=img, timestamp=datetime.fromisoformat(ts), path=path)


def _make_engine(*frames: CapturedFrame) -> CaptureEngine:
    manager = MagicMock()
    engine = CaptureEngine(manager)
    engine.set_target(WindowInfo(id=1, title="Test", app_name="Test"))
    with engine._lock:
        for frame in frames:
            engine._buffer.append(frame)
    return engine


# ---------------------------------------------------------------------------
# List layout / ordering
# ---------------------------------------------------------------------------

def test_newest_frame_is_first(qtbot):
    older = _frame("2024-01-01T10:00:00")
    newer = _frame("2024-01-01T10:05:00")
    engine = _make_engine(older, newer)
    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)

    lw = panel._list_widget
    assert lw.count() == 2
    assert lw.itemWidget(lw.item(0))._frame is newer
    assert lw.itemWidget(lw.item(1))._frame is older


# ---------------------------------------------------------------------------
# Double-click — disk-backed frame
# ---------------------------------------------------------------------------

def test_double_click_disk_backed_frame(qtbot, tmp_path):
    png = tmp_path / "frame.png"
    Image.new("RGB", (10, 10)).save(png)
    frame = _frame("2024-01-01T10:00:00", path=png)
    engine = _make_engine(frame)
    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)

    row_widget = panel._list_widget.itemWidget(panel._list_widget.item(0))

    with patch("drawing_coach.history_panel.QDesktopServices.openUrl", return_value=True) as mock_open:
        qtbot.mouseDClick(row_widget, Qt.MouseButton.LeftButton)

    mock_open.assert_called_once()
    called_url = mock_open.call_args[0][0]
    assert called_url.toLocalFile() == str(png)


# ---------------------------------------------------------------------------
# Double-click — in-memory frame (no disk path)
# ---------------------------------------------------------------------------

def test_double_click_in_memory_frame(qtbot):
    frame = _frame("2024-01-01T10:00:00", path=None)
    engine = _make_engine(frame)
    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)

    row_widget = panel._list_widget.itemWidget(panel._list_widget.item(0))

    with patch("drawing_coach.history_panel.QDesktopServices.openUrl", return_value=True) as mock_open:
        qtbot.mouseDClick(row_widget, Qt.MouseButton.LeftButton)

    mock_open.assert_called_once()
    called_url = mock_open.call_args[0][0]
    local_path = called_url.toLocalFile()
    assert local_path.endswith(".png")
    assert Path(local_path).exists()


# ---------------------------------------------------------------------------
# No default viewer — warning dialog shown
# ---------------------------------------------------------------------------

def test_warning_shown_when_no_viewer(qtbot, tmp_path):
    png = tmp_path / "frame.png"
    Image.new("RGB", (10, 10)).save(png)
    frame = _frame("2024-01-01T10:00:00", path=png)
    engine = _make_engine(frame)
    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)

    row_widget = panel._list_widget.itemWidget(panel._list_widget.item(0))

    from PyQt6.QtWidgets import QMessageBox

    with patch("drawing_coach.history_panel.QDesktopServices.openUrl", return_value=False):
        with patch.object(QMessageBox, "warning") as mock_warn:
            qtbot.mouseDClick(row_widget, Qt.MouseButton.LeftButton)

    mock_warn.assert_called_once()


# ---------------------------------------------------------------------------
# Delete button — hover visibility
# ---------------------------------------------------------------------------

def test_delete_button_hidden_by_default(qtbot):
    engine = _make_engine(_frame("2024-01-01T10:00:00"))
    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)
    panel.show()

    row_widget = panel._list_widget.itemWidget(panel._list_widget.item(0))
    assert row_widget.delete_button.isVisible() is False


def test_delete_button_visible_on_hover_and_hidden_on_leave(qtbot):
    engine = _make_engine(_frame("2024-01-01T10:00:00"))
    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)
    panel.show()

    row_widget = panel._list_widget.itemWidget(panel._list_widget.item(0))

    row_widget.set_hovered(True)
    assert row_widget.delete_button.isVisible() is True

    row_widget.set_hovered(False)
    assert row_widget.delete_button.isVisible() is False


# ---------------------------------------------------------------------------
# Delete button — click removes frame
# ---------------------------------------------------------------------------

def test_clicking_delete_button_removes_row_and_frame(qtbot):
    older = _frame("2024-01-01T10:00:00")
    newer = _frame("2024-01-01T10:05:00")
    engine = _make_engine(older, newer)
    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)

    assert panel._list_widget.count() == 2

    # newest frame is row 0; delete the older one (row 1)
    row_widget = panel._list_widget.itemWidget(panel._list_widget.item(1))
    qtbot.mouseClick(row_widget.delete_button, Qt.MouseButton.LeftButton)

    assert panel._list_widget.count() == 1
    assert engine.get_frames() == [newer]
    remaining_widget = panel._list_widget.itemWidget(panel._list_widget.item(0))
    assert remaining_widget._frame is newer


# ---------------------------------------------------------------------------
# Lookback indicator
# ---------------------------------------------------------------------------

def test_lookback_indicator_highlights_window(qtbot):
    frames = [_frame(f"2024-01-01T10:0{i}:00") for i in range(4)]
    engine = _make_engine(*frames)
    config = LLMConfig(lookback_frames=1)
    panel = HistoryPanel(engine, config)
    qtbot.addWidget(panel)

    # newest-first rendering: row 0 = frames[3], row 1 = frames[2], ...
    for i in range(panel._list_widget.count()):
        widget = panel._list_widget.itemWidget(panel._list_widget.item(i))
        expect_highlighted = i in (0, 1)
        assert (Theme.dialog.lookback_border in widget.styleSheet()) == expect_highlighted


def test_lookback_indicator_zero_highlights_only_latest(qtbot):
    frames = [_frame(f"2024-01-01T10:0{i}:00") for i in range(3)]
    engine = _make_engine(*frames)
    config = LLMConfig(lookback_frames=0)
    panel = HistoryPanel(engine, config)
    qtbot.addWidget(panel)

    for i in range(panel._list_widget.count()):
        widget = panel._list_widget.itemWidget(panel._list_widget.item(i))
        assert (Theme.dialog.lookback_border in widget.styleSheet()) == (i == 0)


def test_lookback_indicator_updates_after_delete(qtbot):
    frames = [_frame(f"2024-01-01T10:0{i}:00") for i in range(3)]
    engine = _make_engine(*frames)
    config = LLMConfig(lookback_frames=0)
    panel = HistoryPanel(engine, config)
    qtbot.addWidget(panel)

    # delete the current latest frame (row 0)
    row_widget = panel._list_widget.itemWidget(panel._list_widget.item(0))
    qtbot.mouseClick(row_widget.delete_button, Qt.MouseButton.LeftButton)

    new_latest_widget = panel._list_widget.itemWidget(panel._list_widget.item(0))
    assert new_latest_widget._frame is frames[1]
    assert Theme.dialog.lookback_border in new_latest_widget.styleSheet()


# ---------------------------------------------------------------------------
# Row hover-highlight
# ---------------------------------------------------------------------------

def test_row_background_highlighted_on_hover_and_cleared_on_leave(qtbot):
    engine = _make_engine(_frame("2024-01-01T10:00:00"))
    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)
    panel.show()

    row_widget = panel._list_widget.itemWidget(panel._list_widget.item(0))
    assert "background" not in row_widget.styleSheet()

    row_widget.set_hovered(True)
    assert "background" in row_widget.styleSheet()

    row_widget.set_hovered(False)
    assert "background" not in row_widget.styleSheet()


def test_mouse_move_over_viewport_drives_row_hover(qtbot):
    # Regression: hover was previously driven by Enter/Leave events delivered
    # directly to the row widget embedded via setItemWidget(), which is
    # unreliable on macOS. This sends real QMouseEvents through the viewport's
    # eventFilter (the actual code path a mouse move dispatches through)
    # rather than calling the widget's hover hook directly, so a delivery
    # regression like that would be caught here. QTest/qtbot's mouseMove
    # warps the real OS cursor, which isn't reliable under Xvfb/offscreen —
    # constructing the QMouseEvent directly keeps this deterministic.
    older = _frame("2024-01-01T10:00:00")
    newer = _frame("2024-01-01T10:05:00")
    engine = _make_engine(older, newer)
    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)
    panel.show()

    lw = panel._list_widget
    first_row = lw.itemWidget(lw.item(0))
    second_row = lw.itemWidget(lw.item(1))

    def _move_to(pos):
        event = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(pos),
            Qt.MouseButton.NoButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(lw.viewport(), event)

    _move_to(lw.visualItemRect(lw.item(0)).center())
    assert first_row.delete_button.isVisible() is True
    assert second_row.delete_button.isVisible() is False

    _move_to(lw.visualItemRect(lw.item(1)).center())
    assert first_row.delete_button.isVisible() is False
    assert second_row.delete_button.isVisible() is True

    QApplication.sendEvent(lw.viewport(), QEvent(QEvent.Type.Leave))
    assert second_row.delete_button.isVisible() is False


def test_hover_text_color_contrasts_with_hover_background_on_dark_theme(qtbot):
    # Regression: a fixed light hover background paired with a dark-theme's
    # default light label text produced unreadable white-on-white text.
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor("#f0f0f0"))
    QApplication.setPalette(dark_palette)
    try:
        engine = _make_engine(_frame("2024-01-01T10:00:00"))
        panel = HistoryPanel(engine, LLMConfig())
        qtbot.addWidget(panel)
        panel.show()

        row_widget = panel._list_widget.itemWidget(panel._list_widget.item(0))
        row_widget.set_hovered(True)

        style = row_widget.styleSheet()
        background = row_widget.palette().color(QPalette.ColorRole.Highlight).name()
        text_color = row_widget.palette().color(
            QPalette.ColorRole.HighlightedText
        ).name()

        assert background.lower() in style.lower()
        assert text_color.lower() in style.lower()
        assert background.lower() != text_color.lower()
    finally:
        QApplication.setPalette(QApplication.style().standardPalette())


def test_lookback_border_survives_hover_enter_and_leave(qtbot):
    frames = [_frame(f"2024-01-01T10:0{i}:00") for i in range(2)]
    engine = _make_engine(*frames)
    config = LLMConfig(lookback_frames=0)
    panel = HistoryPanel(engine, config)
    qtbot.addWidget(panel)
    panel.show()

    # row 0 is the latest frame, which the zero-lookback window highlights.
    row_widget = panel._list_widget.itemWidget(panel._list_widget.item(0))
    assert Theme.dialog.lookback_border in row_widget.styleSheet()

    row_widget.set_hovered(True)
    assert Theme.dialog.lookback_border in row_widget.styleSheet()
    assert "background" in row_widget.styleSheet()

    row_widget.set_hovered(False)
    assert Theme.dialog.lookback_border in row_widget.styleSheet()
    assert "background" not in row_widget.styleSheet()
