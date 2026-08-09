"""Unit tests for FeedbackStore disk persistence."""

import hashlib
import json
from datetime import datetime

from PIL import Image

from drawing_coach.capture_engine import CapturedFrame
from drawing_coach.feedback_engine import FeedbackResponse
from drawing_coach.feedback_store import FeedbackStore


def _response(**overrides) -> FeedbackResponse:
    defaults = dict(
        mode="quick_hint",
        text="Nice work",
        timestamp=datetime(2024, 6, 14, 9, 41, 0),
        annotation_json=None,
        observations=[{"category": "anatomy", "note": "arm ok"}],
        used_structured_output=True,
        frame_hashes=["abc123", "def456"],
    )
    defaults.update(overrides)
    return FeedbackResponse(**defaults)


def _frame() -> CapturedFrame:
    return CapturedFrame(image=Image.new("RGB", (200, 150), (10, 20, 30)))


def _frame_on_disk(session_dir, name: str = "094132_0007.png") -> CapturedFrame:
    """A frame written to `<session>/frames/`, as `CaptureEngine` stores them."""
    frames_dir = session_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    path = frames_dir / name
    image = Image.new("RGB", (200, 150), (10, 20, 30))
    image.save(path, format="PNG")
    return CapturedFrame(image=image, path=path)


def _entry_json(session_dir) -> dict:
    """The single feedback entry JSON written under `session_dir`."""
    entries = list((session_dir / "feedback").glob("*.json"))
    assert len(entries) == 1
    return json.loads(entries[0].read_text())


def test_save_creates_feedback_dir(tmp_path):
    store = FeedbackStore(tmp_path)
    store.save(_response(), _frame())

    assert (tmp_path / "feedback").is_dir()


def test_save_load_round_trip_preserves_all_fields(tmp_path):
    store = FeedbackStore(tmp_path)
    response = _response()
    store.save(response, _frame())

    loaded = store.load()

    assert len(loaded) == 1
    result = loaded[0]
    assert result.mode == response.mode
    assert result.text == response.text
    assert result.timestamp == response.timestamp
    assert result.annotation_json == response.annotation_json
    assert result.observations == response.observations
    assert result.used_structured_output == response.used_structured_output
    assert result.frame_hashes == response.frame_hashes


def test_save_writes_no_thumbnail(tmp_path):
    store = FeedbackStore(tmp_path)
    store.save(_response(), _frame_on_disk(tmp_path))

    assert list((tmp_path / "feedback").glob("*_thumb.jpg")) == []
    assert "thumbnail_path" not in _entry_json(tmp_path)


def test_save_records_session_relative_frame_path(tmp_path):
    store = FeedbackStore(tmp_path)
    store.save(_response(), _frame_on_disk(tmp_path))

    assert _entry_json(tmp_path)["frame_path"] == "frames/094132_0007.png"


def test_save_writes_no_image_file_other_than_overlay(tmp_path):
    store = FeedbackStore(tmp_path)
    store.save(_response(), _frame_on_disk(tmp_path))

    written = sorted(p.name for p in (tmp_path / "feedback").iterdir())
    assert written == ["20240614_094100_quick_hint.json"]


def test_save_without_last_frame_records_null_frame_path(tmp_path):
    store = FeedbackStore(tmp_path)
    store.save(_response(), None)

    assert _entry_json(tmp_path)["frame_path"] is None


def test_save_with_frame_outside_session_records_null_frame_path(tmp_path):
    """A frame with no path, or one outside the session, has nothing to reference."""
    store = FeedbackStore(tmp_path)
    store.save(_response(), _frame())

    assert _entry_json(tmp_path)["frame_path"] is None


def test_save_writes_overlay_png_only_when_overlay_image_supplied(tmp_path):
    store = FeedbackStore(tmp_path)
    response = _response(mode="overlay")
    store.save(response, _frame(), overlay_image=Image.new("RGB", (50, 50)))

    overlay_files = list((tmp_path / "feedback").glob("*_overlay.png"))
    assert len(overlay_files) == 1


def test_save_without_overlay_image_writes_no_overlay_png(tmp_path):
    store = FeedbackStore(tmp_path)
    store.save(_response(), _frame())

    overlay_files = list((tmp_path / "feedback").glob("*_overlay.png"))
    assert overlay_files == []


def test_load_returns_empty_list_when_no_feedback_dir(tmp_path):
    store = FeedbackStore(tmp_path)
    assert store.load() == []


def test_load_skips_malformed_files_with_warning(tmp_path, caplog):
    store = FeedbackStore(tmp_path)
    store.save(_response(), _frame())
    (tmp_path / "feedback" / "20240101_000000_quick_hint.json").write_text("not json")

    with caplog.at_level("WARNING", logger="drawing_coach.feedback_store"):
        loaded = store.load()

    assert len(loaded) == 1
    assert any("malformed" in rec.message.lower() for rec in caplog.records)


def test_load_orders_by_filename(tmp_path):
    store = FeedbackStore(tmp_path)
    first = _response(timestamp=datetime(2024, 1, 1, 9, 0, 0), text="first")
    second = _response(timestamp=datetime(2024, 1, 1, 10, 0, 0), text="second")
    store.save(second, _frame())
    store.save(first, _frame())

    loaded = store.load()

    assert [r.text for r in loaded] == ["first", "second"]


def test_overlay_image_for_returns_image_when_present(tmp_path):
    store = FeedbackStore(tmp_path)
    response = _response(mode="overlay")
    overlay_img = Image.new("RGB", (64, 48), (5, 5, 5))
    store.save(response, _frame(), overlay_image=overlay_img)

    result = store.overlay_image_for(response)

    assert result is not None
    assert (result.width, result.height) == (64, 48)


def test_overlay_image_for_returns_none_when_absent(tmp_path):
    store = FeedbackStore(tmp_path)
    response = _response()
    store.save(response, _frame())

    assert store.overlay_image_for(response) is None


# ---------------------------------------------------------------------------
# frame_path
# ---------------------------------------------------------------------------


def test_load_round_trips_frame_path(tmp_path):
    store = FeedbackStore(tmp_path)
    store.save(_response(), _frame_on_disk(tmp_path))

    assert store.load()[0].frame_path == "frames/094132_0007.png"


def test_load_entry_without_frame_path_key(tmp_path):
    """Entries written before frame paths were recorded still load."""
    store = FeedbackStore(tmp_path)
    store.save(_response(), _frame_on_disk(tmp_path))
    entry = next((tmp_path / "feedback").glob("*.json"))
    data = json.loads(entry.read_text())
    del data["frame_path"]
    data["thumbnail_path"] = "20240614_094100_quick_hint_thumb.jpg"
    entry.write_text(json.dumps(data))

    loaded = store.load()

    assert len(loaded) == 1
    assert loaded[0].frame_path is None
    assert loaded[0].text == "Nice work"


def test_frame_path_for_returns_path_when_frame_exists(tmp_path):
    store = FeedbackStore(tmp_path)
    response = _response()
    store.save(response, _frame_on_disk(tmp_path))

    resolved = store.frame_path_for(store.load()[0])

    assert resolved is not None
    assert resolved.is_file()
    assert resolved == tmp_path / "frames" / "094132_0007.png"


def test_frame_path_for_returns_none_when_never_recorded(tmp_path):
    store = FeedbackStore(tmp_path)
    store.save(_response(), None)

    assert store.frame_path_for(store.load()[0]) is None


def test_frame_path_for_returns_none_when_frame_deleted(tmp_path):
    store = FeedbackStore(tmp_path)
    frame = _frame_on_disk(tmp_path)
    store.save(_response(), frame)
    frame.path.unlink()

    assert store.frame_path_for(store.load()[0]) is None


# ---------------------------------------------------------------------------
# last_entry_for
# ---------------------------------------------------------------------------


def test_last_entry_for_returns_match(tmp_path):
    store = FeedbackStore(tmp_path)
    response = _response(frame_hashes=["a", "b"])
    store.save(response, _frame())

    result = store.last_entry_for("quick_hint", ["a", "b"])

    assert result is not None
    assert result.frame_hashes == ["a", "b"]


def test_last_entry_for_no_match_returns_none(tmp_path):
    store = FeedbackStore(tmp_path)
    store.save(_response(frame_hashes=["a", "b"]), _frame())

    assert store.last_entry_for("quick_hint", ["different"]) is None
    assert store.last_entry_for("full_critique", ["a", "b"]) is None


def test_last_entry_for_empty_history_returns_none(tmp_path):
    store = FeedbackStore(tmp_path)
    assert store.last_entry_for("quick_hint", []) is None


def test_last_entry_for_returns_most_recent_match(tmp_path):
    store = FeedbackStore(tmp_path)
    older = _response(
        timestamp=datetime(2024, 1, 1, 9, 0, 0), text="older", frame_hashes=["x"]
    )
    newer = _response(
        timestamp=datetime(2024, 1, 1, 10, 0, 0), text="newer", frame_hashes=["x"]
    )
    store.save(older, _frame())
    store.save(newer, _frame())

    result = store.last_entry_for("quick_hint", ["x"])

    assert result is not None
    assert result.text == "newer"


# ---------------------------------------------------------------------------
# Frame-hash backfill
# ---------------------------------------------------------------------------


def _live_hash(path) -> str:
    """The hash the live capture path produces for a frame file.

    Mirrors `MainWindow._current_frame_hashes()` over a buffer rebuilt by
    `CaptureEngine._load_frames_from_disk()`.
    """
    return hashlib.sha256(Image.open(path).copy().tobytes()).hexdigest()


def _drop_hashes(session_dir) -> None:
    """Strip `frame_hashes` from the single entry, as older versions wrote it."""
    entry = next((session_dir / "feedback").glob("*.json"))
    data = json.loads(entry.read_text())
    del data["frame_hashes"]
    entry.write_text(json.dumps(data))


def test_last_entry_for_derives_hashes_from_frame_on_disk(tmp_path):
    store = FeedbackStore(tmp_path)
    frame = _frame_on_disk(tmp_path)
    store.save(_response(), frame)
    _drop_hashes(tmp_path)

    result = store.last_entry_for("quick_hint", [_live_hash(frame.path)])

    assert result is not None
    assert result.text == "Nice work"


def test_derived_hash_matches_live_capture_hash(tmp_path):
    """A derived hash and a live hash of the same image must be equal."""
    store = FeedbackStore(tmp_path)
    frame = _frame_on_disk(tmp_path)
    store.save(_response(), frame)
    _drop_hashes(tmp_path)

    derived = store._hashes_for(store.load()[0])

    assert derived == [_live_hash(frame.path)]


def test_deriving_hashes_leaves_entry_json_untouched(tmp_path):
    store = FeedbackStore(tmp_path)
    frame = _frame_on_disk(tmp_path)
    store.save(_response(), frame)
    _drop_hashes(tmp_path)
    entry = next((tmp_path / "feedback").glob("*.json"))
    before = entry.read_bytes()

    store.last_entry_for("quick_hint", [_live_hash(frame.path)])

    assert entry.read_bytes() == before


def test_last_entry_for_empty_hashes_never_matches_unhashed_entry(tmp_path):
    """Regression: `[] == []` used to disable Request Feedback spuriously."""
    store = FeedbackStore(tmp_path)
    store.save(_response(), None)
    _drop_hashes(tmp_path)

    assert store.last_entry_for("quick_hint", []) is None


def test_unhashed_entry_with_deleted_frame_never_matches(tmp_path):
    store = FeedbackStore(tmp_path)
    frame = _frame_on_disk(tmp_path)
    store.save(_response(), frame)
    _drop_hashes(tmp_path)
    expected = _live_hash(frame.path)
    frame.path.unlink()

    assert store.last_entry_for("quick_hint", []) is None
    assert store.last_entry_for("quick_hint", [expected]) is None

    loaded = store.load()
    assert len(loaded) == 1
    assert loaded[0].text == "Nice work"
    assert loaded[0].mode == "quick_hint"
    assert loaded[0].timestamp == datetime(2024, 6, 14, 9, 41, 0)


def test_undecodable_frame_is_logged_and_does_not_raise(tmp_path, caplog):
    store = FeedbackStore(tmp_path)
    frame = _frame_on_disk(tmp_path)
    store.save(_response(), frame)
    _drop_hashes(tmp_path)
    frame.path.write_bytes(b"not a png")

    with caplog.at_level("WARNING", logger="drawing_coach.feedback_store"):
        result = store.last_entry_for("quick_hint", ["anything"])

    assert result is None
    assert any("cannot hash frame" in rec.message.lower() for rec in caplog.records)
    assert len(store.load()) == 1


def test_last_entry_for_empty_hashes_never_matches_recorded_entry(tmp_path):
    store = FeedbackStore(tmp_path)
    store.save(_response(frame_hashes=["a", "b"]), _frame())

    assert store.last_entry_for("quick_hint", []) is None


def test_recorded_hashes_match_without_reading_the_frame(tmp_path, monkeypatch):
    store = FeedbackStore(tmp_path)
    store.save(_response(frame_hashes=["a", "b"]), _frame_on_disk(tmp_path))

    def _fail(*args, **kwargs):
        raise AssertionError("frame image should not be opened for a hashed entry")

    monkeypatch.setattr(Image, "open", _fail)
    result = store.last_entry_for("quick_hint", ["a", "b"])

    assert result is not None
    assert result.frame_hashes == ["a", "b"]
