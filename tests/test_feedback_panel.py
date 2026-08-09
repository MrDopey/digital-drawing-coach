"""Tests for FeedbackPanel default size, mode selection, and overlay resizing."""

import hashlib
import json
from datetime import datetime
from unittest.mock import MagicMock

from PIL import Image
from PyQt6.QtWidgets import QRadioButton

from drawing_coach.capture_engine import CapturedFrame
from drawing_coach.design_system import MutedLabel, PrimaryButton
from drawing_coach.feedback_engine import FeedbackResponse
from drawing_coach.feedback_panel import MODE_LABELS, FeedbackPanel
from drawing_coach.feedback_store import FeedbackStore
from drawing_coach.theme import Theme


def _overlay_response() -> FeedbackResponse:
    return FeedbackResponse(
        mode="overlay", text="Nice work", timestamp=datetime(2024, 1, 1, 10, 0, 0)
    )


# ---------------------------------------------------------------------------
# Default size
# ---------------------------------------------------------------------------


def test_default_size_is_larger_than_old_minimum(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    assert panel.width() > 380
    assert panel.height() > 300


# ---------------------------------------------------------------------------
# Mode selection
# ---------------------------------------------------------------------------


def test_quick_hint_is_selected_by_default(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    assert panel.current_mode() == "quick_hint"


def test_current_mode_reflects_selected_radio_button(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    radios = panel.findChildren(QRadioButton)
    for key in MODE_LABELS:
        target = next(r for r in radios if r.property("mode_key") == key)
        target.setChecked(True)
        assert panel.current_mode() == key


# ---------------------------------------------------------------------------
# In-panel trigger button
# ---------------------------------------------------------------------------


def test_request_button_emits_feedback_requested(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    callback = MagicMock()
    panel.feedback_requested.connect(callback)

    panel._request_btn.click()

    callback.assert_called_once_with(panel.current_mode())


def test_request_button_without_listener_does_not_raise(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    panel._request_btn.click()  # no listener connected


# ---------------------------------------------------------------------------
# Overlay resizing and zoom
# ---------------------------------------------------------------------------


def test_overlay_image_keeps_zoom_level_on_panel_resize(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)
    panel.show()

    overlay_img = Image.new("RGB", (400, 300), (10, 20, 30))
    panel.show_feedback(_overlay_response(), overlay_image=overlay_img)

    original_pixmap = panel._image_label.pixmap()
    assert original_pixmap is not None
    original_size = original_pixmap.size()

    panel.resize(panel.width() + 200, panel.height() + 150)
    qtbot.wait(10)

    resized_pixmap = panel._image_label.pixmap()
    assert resized_pixmap is not None
    resized_size = resized_pixmap.size()

    assert (resized_size.width(), resized_size.height()) == (
        original_size.width(),
        original_size.height(),
    )


def test_zoom_in_and_out_change_pixmap_size(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    overlay_img = Image.new("RGB", (400, 300), (10, 20, 30))
    panel.show_feedback(_overlay_response(), overlay_image=overlay_img)
    original_size = panel._image_label.pixmap().size()

    panel._zoom_in()
    zoomed_in_size = panel._image_label.pixmap().size()
    assert zoomed_in_size.width() > original_size.width()

    panel._zoom_reset()
    reset_size = panel._image_label.pixmap().size()
    assert (reset_size.width(), reset_size.height()) == (
        original_size.width(),
        original_size.height(),
    )

    panel._zoom_out()
    zoomed_out_size = panel._image_label.pixmap().size()
    assert zoomed_out_size.width() < original_size.width()


# ---------------------------------------------------------------------------
# Design-system components (theme-driven styling, not raw QSS strings)
# ---------------------------------------------------------------------------


def test_panel_uses_overlay_background(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    assert Theme.overlay.background in panel.styleSheet()


def test_request_and_history_buttons_are_primary_buttons(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    assert isinstance(panel._request_btn, PrimaryButton)
    assert isinstance(panel._prev_btn, PrimaryButton)
    assert isinstance(panel._next_btn, PrimaryButton)


def test_zoom_and_history_labels_are_muted_labels(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    assert isinstance(panel._zoom_label, MutedLabel)
    assert isinstance(panel._hist_label, MutedLabel)
    assert Theme.overlay.muted_text_dim in panel._zoom_label.styleSheet()


def test_zoom_resets_on_history_navigation(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    overlay_img = Image.new("RGB", (400, 300), (10, 20, 30))
    panel.show_feedback(_overlay_response(), overlay_image=overlay_img)
    panel._zoom_in()
    assert panel._zoom_factor != 1.0

    panel.show_feedback(
        FeedbackResponse(
            mode="quick_hint", text="ok", timestamp=datetime(2024, 1, 1, 10, 1, 0)
        )
    )
    panel._show_prev()

    assert panel._zoom_factor == 1.0


# ---------------------------------------------------------------------------
# Request Feedback deduplication
# ---------------------------------------------------------------------------


def _store_with_entry(tmp_path, mode="quick_hint", frame_hashes=("abc",)):
    store = FeedbackStore(tmp_path)
    frame = CapturedFrame(image=Image.new("RGB", (100, 100)))
    store.save(
        FeedbackResponse(mode=mode, text="ok", frame_hashes=list(frame_hashes)),
        frame,
    )
    return store


def test_update_request_state_disables_button_on_match(tmp_path, qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)
    panel.set_store(_store_with_entry(tmp_path))

    panel.update_request_state(["abc"])

    assert not panel._request_btn.isEnabled()
    assert panel._request_btn.toolTip() == "Already generated for this drawing and mode"


def test_update_request_state_reenables_on_new_frame(tmp_path, qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)
    panel.set_store(_store_with_entry(tmp_path))
    panel.update_request_state(["abc"])
    assert not panel._request_btn.isEnabled()

    panel.update_request_state(["a-new-hash"])

    assert panel._request_btn.isEnabled()
    assert panel._request_btn.toolTip() == ""


def test_update_request_state_reenables_on_mode_change(tmp_path, qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)
    panel.set_store(_store_with_entry(tmp_path, mode="quick_hint"))
    panel.update_request_state(["abc"])
    assert not panel._request_btn.isEnabled()

    radios = panel.findChildren(QRadioButton)
    other_mode = next(r for r in radios if r.property("mode_key") == "full_critique")
    other_mode.setChecked(True)
    panel.update_request_state(["abc"])

    assert panel._request_btn.isEnabled()


def test_update_request_state_enabled_with_no_history(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    panel.update_request_state(["anything"])

    assert panel._request_btn.isEnabled()


def _store_with_unhashed_entry(tmp_path, mode="quick_hint"):
    """A store whose one entry predates frame-hash tracking, with its frame on disk."""
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_path = frames_dir / "094132_0007.png"
    Image.new("RGB", (120, 90), (7, 8, 9)).save(frame_path, format="PNG")

    store = FeedbackStore(tmp_path)
    store.save(
        FeedbackResponse(mode=mode, text="ok", frame_hashes=[]),
        CapturedFrame(image=Image.open(frame_path).copy(), path=frame_path),
    )
    entry = next((tmp_path / "feedback").glob("*.json"))
    data = json.loads(entry.read_text())
    del data["frame_hashes"]
    entry.write_text(json.dumps(data))

    live_hash = hashlib.sha256(Image.open(frame_path).copy().tobytes()).hexdigest()
    return store, live_hash


def test_update_request_state_enabled_with_no_frames_captured(tmp_path, qtbot):
    """Regression: an entry with no frame hashes used to match an empty frame set."""
    panel = FeedbackPanel()
    qtbot.addWidget(panel)
    store, _ = _store_with_unhashed_entry(tmp_path)
    panel.set_store(store)

    panel.update_request_state([])

    assert panel._request_btn.isEnabled()
    assert panel._request_btn.toolTip() == ""


def test_update_request_state_disables_button_on_backfilled_match(tmp_path, qtbot):
    """An entry whose hashes came from disk de-duplicates like a recorded one."""
    panel = FeedbackPanel()
    qtbot.addWidget(panel)
    store, live_hash = _store_with_unhashed_entry(tmp_path)
    panel.set_store(store)

    panel.update_request_state([live_hash])

    assert not panel._request_btn.isEnabled()
    assert panel._request_btn.toolTip() == "Already generated for this drawing and mode"


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------


def test_sidebar_row_click_navigates_and_stays_synced_with_prev_next(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    panel.show_feedback(
        FeedbackResponse(
            mode="quick_hint", text="first", timestamp=datetime(2024, 1, 1, 10, 0, 0)
        )
    )
    panel.show_feedback(
        FeedbackResponse(
            mode="full_critique",
            text="second",
            timestamp=datetime(2024, 1, 1, 10, 5, 0),
        )
    )
    assert panel._sidebar.count() == 2

    # row 0 is the newest ("second"); click row 1 ("first")
    panel._sidebar.setCurrentRow(1)

    assert panel._history_idx == 0
    assert panel._text_edit.toPlainText().strip() == "first"

    panel._show_next()

    assert panel._history_idx == 1
    assert panel._sidebar.currentRow() == 0
    assert panel._text_edit.toPlainText().strip() == "second"


# ---------------------------------------------------------------------------
# Structured observations
# ---------------------------------------------------------------------------


def test_show_feedback_renders_observations_alongside_text(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    panel.show_feedback(
        FeedbackResponse(
            mode="full_critique",
            text="Great progress overall.",
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
            observations=[
                {"category": "anatomy", "note": "eyes are too wide apart."},
                {"category": "anatomy", "note": "jawline is too angular."},
                {"category": "gesture", "note": "pose flow has improved."},
            ],
        )
    )

    shown = panel._text_edit.toPlainText()
    assert "Great progress overall." in shown
    assert "eyes are too wide apart." in shown
    assert "jawline is too angular." in shown
    assert "pose flow has improved." in shown


def test_show_feedback_with_no_observations_shows_only_text(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    panel.show_feedback(
        FeedbackResponse(
            mode="quick_hint",
            text="Nice work",
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
        )
    )

    assert panel._text_edit.toPlainText().strip() == "Nice work"


# ---------------------------------------------------------------------------
# Full-resolution frame display (one image path for every mode)
# ---------------------------------------------------------------------------


def _frame_on_disk(session_dir, size=(640, 480)) -> CapturedFrame:
    """A frame written to `<session>/frames/`, as `CaptureEngine` stores them."""
    frames_dir = session_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    path = frames_dir / "094132_0007.png"
    image = Image.new("RGB", size, (10, 20, 30))
    image.save(path, format="PNG")
    return CapturedFrame(image=image, path=path)


def _panel_with_store(tmp_path, qtbot) -> FeedbackPanel:
    panel = FeedbackPanel()
    qtbot.addWidget(panel)
    panel.set_store(FeedbackStore(tmp_path))
    return panel


def test_non_overlay_entry_shows_frame_at_full_resolution(tmp_path, qtbot):
    panel = _panel_with_store(tmp_path, qtbot)

    panel.show_feedback(
        FeedbackResponse(mode="quick_hint", text="ok"),
        last_frame=_frame_on_disk(tmp_path, size=(640, 480)),
    )

    assert not panel._image_pane.isHidden()
    pixmap = panel._image_label.pixmap()
    assert pixmap is not None
    assert (pixmap.width(), pixmap.height()) == (640, 480)


def test_non_overlay_entry_hides_save_overlay_button(tmp_path, qtbot):
    panel = _panel_with_store(tmp_path, qtbot)

    panel.show_feedback(
        FeedbackResponse(mode="quick_hint", text="ok"),
        last_frame=_frame_on_disk(tmp_path),
    )

    assert panel._save_btn.isHidden()


def test_overlay_entry_shows_composited_image_and_save_button(tmp_path, qtbot):
    panel = _panel_with_store(tmp_path, qtbot)

    panel.show_feedback(
        _overlay_response(),
        overlay_image=Image.new("RGB", (400, 300), (10, 20, 30)),
        last_frame=_frame_on_disk(tmp_path, size=(640, 480)),
    )

    assert not panel._image_pane.isHidden()
    pixmap = panel._image_label.pixmap()
    assert (pixmap.width(), pixmap.height()) == (400, 300)
    assert not panel._save_btn.isHidden()


def test_entry_without_frame_path_hides_image_pane(tmp_path, qtbot):
    panel = _panel_with_store(tmp_path, qtbot)

    panel.show_feedback(FeedbackResponse(mode="quick_hint", text="ok"))

    assert panel._image_pane.isHidden()
    assert panel._current_pixmap is None
    assert "ok" in panel._text_edit.toPlainText()


def test_entry_with_dangling_frame_path_hides_image_pane(tmp_path, qtbot):
    panel = _panel_with_store(tmp_path, qtbot)
    frame = _frame_on_disk(tmp_path)
    panel.show_feedback(FeedbackResponse(mode="quick_hint", text="ok"), last_frame=frame)
    frame.path.unlink()

    panel.set_store(FeedbackStore(tmp_path))

    assert panel._image_pane.isHidden()
    assert panel._current_pixmap is None


def test_zoom_changes_pixmap_size_for_non_overlay_frame(tmp_path, qtbot):
    panel = _panel_with_store(tmp_path, qtbot)
    panel.show_feedback(
        FeedbackResponse(mode="quick_hint", text="ok"),
        last_frame=_frame_on_disk(tmp_path, size=(640, 480)),
    )
    original_width = panel._image_label.pixmap().width()

    panel._zoom_in()
    assert panel._image_label.pixmap().width() > original_width

    panel._zoom_out()
    assert panel._image_label.pixmap().width() == original_width


def test_zoom_resets_on_navigation_between_non_overlay_frames(tmp_path, qtbot):
    panel = _panel_with_store(tmp_path, qtbot)
    panel.show_feedback(
        FeedbackResponse(
            mode="quick_hint", text="first", timestamp=datetime(2024, 1, 1, 10, 0, 0)
        ),
        last_frame=_frame_on_disk(tmp_path),
    )
    panel._zoom_in()
    assert panel._zoom_factor != 1.0

    panel.show_feedback(
        FeedbackResponse(
            mode="quick_hint", text="second", timestamp=datetime(2024, 1, 1, 10, 1, 0)
        ),
        last_frame=_frame_on_disk(tmp_path),
    )

    assert panel._zoom_factor == 1.0
    assert panel._zoom_label.text() == "100%"


# ---------------------------------------------------------------------------
# set_store
# ---------------------------------------------------------------------------


def test_set_store_loads_existing_session_history(tmp_path, qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)
    store = _store_with_entry(tmp_path, mode="quick_hint", frame_hashes=("abc",))

    panel.set_store(store)

    assert panel._sidebar.count() == 1
    assert len(panel._history) == 1
    assert panel._history_idx == 0


def test_set_store_clears_previously_bound_session_entries(tmp_path, qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)
    store_a = _store_with_entry(tmp_path / "a", mode="quick_hint")
    store_b = FeedbackStore(tmp_path / "b")  # empty session, nothing saved

    panel.set_store(store_a)
    assert panel._sidebar.count() == 1

    panel.set_store(store_b)

    assert panel._sidebar.count() == 0
    assert panel._history == []
    assert panel._overlay_images == {}
    assert panel._history_idx == -1
