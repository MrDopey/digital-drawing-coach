"""Tests for HistoryPanel list layout, ordering, and open-image behaviour."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image
from PyQt6.QtCore import Qt

from drawing_coach.capture_engine import CapturedFrame
from drawing_coach.history_panel import HistoryPanel


def _frame(ts: str, path: Path | None = None) -> CapturedFrame:
    img = Image.new("RGB", (10, 10), (100, 100, 100))
    return CapturedFrame(image=img, timestamp=datetime.fromisoformat(ts), path=path)


# ---------------------------------------------------------------------------
# List layout / ordering
# ---------------------------------------------------------------------------

def test_newest_frame_is_first(qtbot):
    older = _frame("2024-01-01T10:00:00")
    newer = _frame("2024-01-01T10:05:00")
    panel = HistoryPanel([older, newer])
    qtbot.addWidget(panel)

    list_widget = panel.findChild(type(panel).__mro__[0].__mro__[0])  # walk up
    # Find the QListWidget via children
    from PyQt6.QtWidgets import QListWidget
    lw = panel.findChild(QListWidget)
    assert lw is not None
    assert lw.item(0).text() == newer.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    assert lw.item(1).text() == older.timestamp.strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Double-click — disk-backed frame
# ---------------------------------------------------------------------------

def test_double_click_disk_backed_frame(qtbot, tmp_path):
    png = tmp_path / "frame.png"
    Image.new("RGB", (10, 10)).save(png)
    frame = _frame("2024-01-01T10:00:00", path=png)
    panel = HistoryPanel([frame])
    qtbot.addWidget(panel)

    from PyQt6.QtWidgets import QListWidget
    lw = panel.findChild(QListWidget)

    with patch("drawing_coach.history_panel.QDesktopServices.openUrl", return_value=True) as mock_open:
        lw.itemDoubleClicked.emit(lw.item(0))

    mock_open.assert_called_once()
    called_url = mock_open.call_args[0][0]
    assert called_url.toLocalFile() == str(png)


# ---------------------------------------------------------------------------
# Double-click — in-memory frame (no disk path)
# ---------------------------------------------------------------------------

def test_double_click_in_memory_frame(qtbot):
    frame = _frame("2024-01-01T10:00:00", path=None)
    panel = HistoryPanel([frame])
    qtbot.addWidget(panel)

    from PyQt6.QtWidgets import QListWidget
    lw = panel.findChild(QListWidget)

    with patch("drawing_coach.history_panel.QDesktopServices.openUrl", return_value=True) as mock_open:
        lw.itemDoubleClicked.emit(lw.item(0))

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
    panel = HistoryPanel([frame])
    qtbot.addWidget(panel)

    from PyQt6.QtWidgets import QListWidget, QMessageBox
    lw = panel.findChild(QListWidget)

    with patch("drawing_coach.history_panel.QDesktopServices.openUrl", return_value=False):
        with patch.object(QMessageBox, "warning") as mock_warn:
            lw.itemDoubleClicked.emit(lw.item(0))

    mock_warn.assert_called_once()
