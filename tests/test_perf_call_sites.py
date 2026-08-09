"""Instrumentation must be observationally neutral.

The probes live inside the very code under suspicion, so the risk worth testing
is that they change behaviour or become a cost of their own. Every test here
runs the same assertion with perf.ON both false and true.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image

from drawing_coach import perf
from drawing_coach.capture_engine import CapturedFrame, CaptureEngine
from drawing_coach.history_panel import HistoryPanel, _pil_to_pixmap
from drawing_coach.llm_config import LLMConfig
from drawing_coach.window_manager import WindowInfo


@pytest.fixture(autouse=True)
def _reset_perf():
    perf.reset_for_tests()
    yield
    perf.reset_for_tests()


@pytest.fixture
def perf_records():
    log = logging.getLogger("drawing_coach.perf")
    captured: list[logging.LogRecord] = []

    class _Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    handler = _Collector()
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    prev = log.propagate
    log.propagate = False
    try:
        yield captured
    finally:
        log.removeHandler(handler)
        log.propagate = prev


def _frame(ts: str, path: Path | None = None) -> CapturedFrame:
    return CapturedFrame(
        image=Image.new("RGB", (10, 10), (100, 100, 100)),
        timestamp=datetime.fromisoformat(ts),
        path=path,
    )


def _make_engine(*frames: CapturedFrame) -> CaptureEngine:
    engine = CaptureEngine(MagicMock())
    engine.set_target(WindowInfo(id=1, title="Test", app_name="Test"))
    with engine._lock:
        for frame in frames:
            engine._buffer.append(frame)
    return engine


def _messages(records) -> list[str]:
    return [r.getMessage() for r in records]


# ---------------------------------------------------------------------------
# HistoryPanel behaviour is identical either way
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("enabled", [False, True])
def test_panel_renders_the_same_rows_with_and_without_instrumentation(
    qtbot, enabled
):
    perf.init("1" if enabled else "0")
    older, newer = _frame("2024-01-01T10:00:00"), _frame("2024-01-01T10:05:00")
    engine = _make_engine(older, newer)

    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)

    lw = panel._list_widget
    assert lw.count() == 2
    assert lw.itemWidget(lw.item(0))._frame is newer
    assert lw.itemWidget(lw.item(1))._frame is older


@pytest.mark.parametrize("enabled", [False, True])
def test_hover_still_works_with_and_without_instrumentation(qtbot, enabled):
    perf.init("1" if enabled else "0")
    engine = _make_engine(_frame("2024-01-01T10:00:00"))
    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)
    panel.show()

    row = panel._list_widget.itemWidget(panel._list_widget.item(0))
    panel._set_hovered_row(row)
    assert row._is_hovered is True
    assert row.delete_button.isVisible() is True

    panel._set_hovered_row(None)
    assert row._is_hovered is False


@pytest.mark.parametrize("enabled", [False, True])
def test_thumbnail_output_is_identical_with_and_without_instrumentation(enabled):
    perf.init("1" if enabled else "0")
    pixmap = _pil_to_pixmap(_frame("2024-01-01T10:00:00"))
    assert (pixmap.width(), pixmap.height()) == (10, 10)


@pytest.mark.parametrize("enabled", [False, True])
def test_paint_event_runs_either_way(qtbot, enabled):
    perf.init("1" if enabled else "0")
    engine = _make_engine(_frame("2024-01-01T10:00:00"))
    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)
    panel.show()
    qtbot.waitExposed(panel)

    row = panel._list_widget.itemWidget(panel._list_widget.item(0))
    row.set_hovered(True)
    row.repaint()  # must not raise with the probe wrapper in place
    assert row._is_hovered is True


# ---------------------------------------------------------------------------
# The probes actually fire when enabled
# ---------------------------------------------------------------------------

def test_render_emits_a_probe_with_counts(qtbot, perf_records):
    perf.init("1")
    engine = _make_engine(_frame("2024-01-01T10:00:00"))
    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)

    render = next(
        m for m in _messages(perf_records) if "PERF label=history.render" in m
    )
    assert "frames=1" in render
    assert "rows=1" in render
    assert "panels=1" in render
    assert "receivers=1" in render
    # Row construction and thumbnailing fold in rather than emitting lines.
    assert "c.history.row_widget.n=1" in render
    assert "c.history.pil_to_pixmap.n=1" in render


def test_render_reports_leaked_panels_still_subscribed(qtbot, perf_records):
    perf.init("1")
    engine = _make_engine(_frame("2024-01-01T10:00:00"))
    first = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(first)
    perf_records.clear()

    second = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(second)

    render = next(
        m for m in _messages(perf_records) if "PERF label=history.render" in m
    )
    assert "panels=2" in render
    assert "receivers=2" in render


def test_hover_hit_test_aggregates_rather_than_logging_each_move(
    qtbot, perf_records
):
    """Per-event lines would be unreadable; the count is what's diagnostic."""
    from PyQt6.QtCore import QEvent, QPointF, Qt
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtWidgets import QApplication

    perf.init("1")
    engine = _make_engine(_frame("2024-01-01T10:00:00"), _frame("2024-01-01T10:05:00"))
    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)
    panel.show()
    lw = panel._list_widget
    perf_records.clear()

    for i in range(50):
        pos = lw.visualItemRect(lw.item(i % 2)).center()
        QApplication.sendEvent(
            lw.viewport(),
            QMouseEvent(
                QEvent.Type.MouseMove,
                QPointF(pos),
                Qt.MouseButton.NoButton,
                Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier,
            ),
        )

    assert not any("hover_hit_test" in m for m in _messages(perf_records))

    perf.flush_aggregates()
    agg = next(m for m in _messages(perf_records) if "history.hover_hit_test" in m)
    assert agg.startswith("PERF-AGG")
    assert "n=50" in agg


def test_no_probe_output_when_instrumentation_is_off(qtbot, perf_records):
    perf.init("0")
    engine = _make_engine(_frame("2024-01-01T10:00:00"))
    panel = HistoryPanel(engine, LLMConfig())
    qtbot.addWidget(panel)
    panel._render()
    perf.flush_aggregates()
    assert _messages(perf_records) == []


# ---------------------------------------------------------------------------
# CaptureEngine
# ---------------------------------------------------------------------------

def _capture_manager(tmp_path):
    manager = MagicMock()
    manager.get_window_rect.return_value = (0, 0, 20, 20)
    manager.capture_image.return_value = Image.new("RGB", (20, 20), (7, 7, 7))
    return manager


@pytest.mark.parametrize("enabled", [False, True])
def test_capture_stores_a_frame_either_way(tmp_path, enabled):
    perf.init("1" if enabled else "0")
    engine = CaptureEngine(_capture_manager(tmp_path))
    engine.set_target(WindowInfo(id=1, title="T", app_name="T"))
    engine._session_dir = tmp_path
    (tmp_path / "frames").mkdir(exist_ok=True)

    frame = engine._do_capture()
    assert frame is not None
    assert engine.get_frames() == [frame]


def test_capture_probe_splits_the_cycle_by_phase(tmp_path, perf_records):
    perf.init("1")
    engine = CaptureEngine(_capture_manager(tmp_path))
    engine.set_target(WindowInfo(id=1, title="T", app_name="T"))
    engine._session_dir = tmp_path
    (tmp_path / "frames").mkdir(exist_ok=True)

    engine._do_capture()

    line = next(
        m for m in _messages(perf_records) if "PERF label=capture.do_capture" in m
    )
    assert "px=20x20" in line
    assert "wrote=1" in line
    for phase in ("get_window_rect", "capture_image", "write_png",
                  "emit_frames_changed"):
        assert f"c.capture.{phase}.n=1" in line


def test_duplicate_capture_is_reported_as_not_written(tmp_path, perf_records):
    perf.init("1")
    engine = CaptureEngine(_capture_manager(tmp_path))
    engine.set_target(WindowInfo(id=1, title="T", app_name="T"))
    engine._session_dir = tmp_path
    (tmp_path / "frames").mkdir(exist_ok=True)

    engine._do_capture()
    perf_records.clear()
    engine._do_capture()  # identical image -> MAE 0 -> discarded

    line = next(
        m for m in _messages(perf_records) if "PERF label=capture.do_capture" in m
    )
    assert "wrote=0" in line
    assert "c.capture.compute_mae.n=1" in line
    assert "c.capture.write_png" not in line
