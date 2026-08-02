"""Unit tests for CaptureEngine ring buffer behaviour."""

import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from drawing_coach.capture_engine import CapturedFrame, CaptureEngine
from drawing_coach.window_manager import WindowInfo


def _make_engine() -> CaptureEngine:
    manager = MagicMock()
    manager.get_window_rect.return_value = (0, 0, 100, 100)
    manager.capture_image.return_value = Image.new("RGB", (100, 100), (128, 128, 128))
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


# ---------------------------------------------------------------------------
# _do_capture delegates image capture to the backend (not mss directly)
# ---------------------------------------------------------------------------

def test_do_capture_calls_manager_capture_image(tmp_path):
    engine = _make_engine()
    engine._session_dir = tmp_path
    (tmp_path / "frames").mkdir()

    frame = engine._do_capture()

    engine._manager.capture_image.assert_called_once_with(engine.target.id)
    assert frame is not None
    assert frame.image is engine._manager.capture_image.return_value


def test_do_capture_never_instantiates_mss_directly(tmp_path):
    engine = _make_engine()
    engine._session_dir = tmp_path
    (tmp_path / "frames").mkdir()

    with patch("mss.mss") as mock_mss_ctor:
        engine._do_capture()

    mock_mss_ctor.assert_not_called()


def test_do_capture_treats_none_image_as_window_lost(tmp_path):
    engine = _make_engine()
    engine._session_dir = tmp_path
    (tmp_path / "frames").mkdir()
    engine._manager.capture_image.return_value = None

    lost: list[bool] = []
    engine.on_window_lost = lambda: lost.append(True)

    frame = engine._do_capture()

    assert frame is None
    assert lost == [True]


# ---------------------------------------------------------------------------
# remove_frame
# ---------------------------------------------------------------------------

def test_remove_frame_removes_from_buffer_without_deleting_file(tmp_path):
    engine = _make_engine()
    frame_to_keep = _fake_frame(engine)
    png = tmp_path / "frame.png"
    Image.new("RGB", (10, 10)).save(png)
    frame_to_delete = CapturedFrame(image=Image.new("RGB", (10, 10)), path=png)
    with engine._lock:
        engine._buffer.append(frame_to_delete)

    received = MagicMock()
    engine.frames_changed.connect(received)

    engine.remove_frame(frame_to_delete)

    frames = engine.get_frames()
    assert frames == [frame_to_keep]
    assert png.exists()
    received.assert_called_once()


def test_remove_frame_unknown_frame_is_noop():
    engine = _make_engine()
    kept = _fake_frame(engine)
    unknown = CapturedFrame(image=Image.new("RGB", (10, 10)))

    received = MagicMock()
    engine.frames_changed.connect(received)

    engine.remove_frame(unknown)

    assert engine.get_frames() == [kept]
    received.assert_not_called()


# ---------------------------------------------------------------------------
# Write-error surfacing
# ---------------------------------------------------------------------------

def test_write_frame_logs_warning_on_failure(tmp_path, caplog):
    engine = _make_engine()
    engine._session_dir = tmp_path
    (tmp_path / "frames").mkdir()
    img = Image.new("RGB", (10, 10))
    with patch.object(img, "save", side_effect=OSError("disk full")):
        with caplog.at_level(logging.WARNING, logger="drawing_coach.capture_engine"):
            result = engine._write_frame(img)
    assert result is None
    assert any("Frame write failed" in r.message for r in caplog.records)


def test_write_frame_calls_on_write_error_callback(tmp_path):
    engine = _make_engine()
    engine._session_dir = tmp_path
    (tmp_path / "frames").mkdir()

    received: list[tuple] = []
    engine.on_write_error = lambda path, exc: received.append((path, exc))

    img = Image.new("RGB", (10, 10))
    err = OSError("disk full")
    with patch.object(img, "save", side_effect=err):
        engine._write_frame(img)

    assert len(received) == 1
    called_path, called_exc = received[0]
    assert called_path.parent == tmp_path / "frames"
    assert called_exc is err


def test_write_frame_no_callback_no_error(tmp_path):
    """on_write_error=None must not raise when a write fails."""
    engine = _make_engine()
    engine._session_dir = tmp_path
    (tmp_path / "frames").mkdir()
    img = Image.new("RGB", (10, 10))
    with patch.object(img, "save", side_effect=OSError("disk full")):
        result = engine._write_frame(img)
    assert result is None


# ---------------------------------------------------------------------------
# meta.json — name field
# ---------------------------------------------------------------------------

def test_write_meta_default_name_includes_app(tmp_path):
    manager = MagicMock()
    engine = CaptureEngine(manager)
    engine.set_target(WindowInfo(id=1, title="Test", app_name="Krita"))
    engine._session_dir = tmp_path
    engine._write_meta()

    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["name"].endswith(" | Krita")
    assert meta["drawing_app"] == "Krita"


def test_write_meta_default_name_omits_app_when_no_target(tmp_path):
    manager = MagicMock()
    engine = CaptureEngine(manager)
    engine._session_dir = tmp_path
    engine._write_meta()

    meta = json.loads((tmp_path / "meta.json").read_text())
    assert "|" not in meta["name"]


def test_write_meta_preserves_existing_custom_name(tmp_path):
    (tmp_path / "meta.json").write_text(
        json.dumps({"start_time": "2026-06-14T09:41:00", "name": "My Study"})
    )
    manager = MagicMock()
    engine = CaptureEngine(manager)
    engine._session_dir = tmp_path
    engine._write_meta()

    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["name"] == "My Study"


# ---------------------------------------------------------------------------
# load_session / new_session
# ---------------------------------------------------------------------------

def test_load_session_writes_end_time_for_previous_session(tmp_path):
    old_dir = tmp_path / "old"
    old_dir.mkdir()
    (old_dir / "frames").mkdir()
    (old_dir / "meta.json").write_text(json.dumps({"start_time": "2026-06-14T09:00:00"}))

    new_dir = tmp_path / "new"
    new_dir.mkdir()
    (new_dir / "frames").mkdir()
    (new_dir / "meta.json").write_text(json.dumps({"start_time": "2026-06-14T10:00:00"}))

    manager = MagicMock()
    engine = CaptureEngine(manager)
    engine._session_dir = old_dir

    engine.load_session(new_dir)

    old_meta = json.loads((old_dir / "meta.json").read_text())
    assert "end_time" in old_meta
    assert engine.session_dir == new_dir


def test_new_session_creates_fresh_directory_and_clears_buffer(tmp_path):
    manager = MagicMock()
    engine = CaptureEngine(manager)
    win = WindowInfo(id=1, title="Test", app_name="Test")
    engine.set_target(win)
    engine._session_dir = tmp_path / "old"
    (engine._session_dir / "frames").mkdir(parents=True)
    engine._write_meta()
    _fake_frame(engine)

    with patch("drawing_coach.capture_engine.sessions_dir", return_value=tmp_path):
        engine.new_session()

    assert engine.session_dir != tmp_path / "old"
    assert engine.session_dir.parent == tmp_path
    assert engine.get_frames() == []
    assert (engine.session_dir / "meta.json").exists()
