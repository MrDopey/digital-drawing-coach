"""Unit tests for FeedbackStore disk persistence."""

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


def test_save_writes_thumbnail_always(tmp_path):
    store = FeedbackStore(tmp_path)
    store.save(_response(), _frame())

    thumb_files = list((tmp_path / "feedback").glob("*_thumb.jpg"))
    assert len(thumb_files) == 1


def test_save_without_last_frame_writes_no_thumbnail(tmp_path):
    store = FeedbackStore(tmp_path)
    store.save(_response(), None)

    thumb_files = list((tmp_path / "feedback").glob("*_thumb.jpg"))
    assert thumb_files == []


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


def test_thumbnail_path_for_returns_none_when_absent(tmp_path):
    store = FeedbackStore(tmp_path)
    response = _response()
    store.save(response, None)

    assert store.thumbnail_path_for(response) is None


def test_thumbnail_path_for_returns_path_when_present(tmp_path):
    store = FeedbackStore(tmp_path)
    response = _response()
    store.save(response, _frame())

    thumb_path = store.thumbnail_path_for(response)

    assert thumb_path is not None
    assert thumb_path.is_file()


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
