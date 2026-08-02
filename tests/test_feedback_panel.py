"""Tests for FeedbackPanel default size, mode selection, and overlay resizing."""

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


def test_thumbnail_caption_is_muted_label(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    assert isinstance(panel._thumb_caption, MutedLabel)


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
