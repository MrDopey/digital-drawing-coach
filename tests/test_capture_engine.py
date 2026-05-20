"""Unit tests for CaptureEngine ring buffer behaviour."""

from unittest.mock import MagicMock

from PIL import Image

from drawing_coach.capture_engine import CapturedFrame, CaptureEngine
from drawing_coach.window_manager import WindowInfo


def _make_engine() -> CaptureEngine:
    manager = MagicMock()
    manager.get_window_rect.return_value = (0, 0, 100, 100)
    engine = CaptureEngine(manager)
    win = WindowInfo(id=1, title="Test", app_name="Test")
    engine.set_target(win)
    return engine


def _fake_frame(engine: CaptureEngine) -> CapturedFrame:
    img = Image.new("RGB", (100, 100), (128, 128, 128))
    frame = CapturedFrame(image=img)
    with engine._lock:
        engine._buffer.append(frame)
    return frame


def test_buffer_starts_empty():
    engine = _make_engine()
    assert engine.get_frames() == []


def test_frames_stored_in_order():
    engine = _make_engine()
    f1 = _fake_frame(engine)
    f2 = _fake_frame(engine)
    frames = engine.get_frames()
    assert frames[0] is f1
    assert frames[1] is f2


def test_buffer_overflow_drops_oldest():
    engine = _make_engine()
    frames = [_fake_frame(engine) for _ in range(CaptureEngine.BUFFER_SIZE + 5)]
    stored = engine.get_frames()
    assert len(stored) == CaptureEngine.BUFFER_SIZE
    assert stored[0] is frames[5]  # oldest 5 dropped


def test_pause_prevents_capture():
    engine = _make_engine()
    engine.pause()
    assert engine.paused is True
    engine.resume()
    assert engine.paused is False


def test_interval_clamped():
    engine = _make_engine()
    engine.interval = 1  # below min
    assert engine.interval == 5
    engine.interval = 9999  # above max
    assert engine.interval == 300


def test_get_frames_returns_copy():
    engine = _make_engine()
    _fake_frame(engine)
    a = engine.get_frames()
    _fake_frame(engine)
    b = engine.get_frames()
    assert len(a) == 1
    assert len(b) == 2
