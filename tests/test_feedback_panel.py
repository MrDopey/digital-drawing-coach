"""Tests for FeedbackPanel default size, mode selection, and overlay resizing."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from PIL import Image
from PyQt6.QtWidgets import QRadioButton

from drawing_coach.feedback_engine import FeedbackResponse
from drawing_coach.feedback_panel import MODE_LABELS, FeedbackPanel


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

def test_trigger_button_invokes_callback(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    callback = MagicMock()
    panel.on_trigger_requested = callback

    panel._trigger_btn.click()

    callback.assert_called_once()


def test_trigger_button_without_callback_does_not_raise(qtbot):
    panel = FeedbackPanel()
    qtbot.addWidget(panel)

    panel._trigger_btn.click()  # on_trigger_requested is None by default


# ---------------------------------------------------------------------------
# Overlay resizing
# ---------------------------------------------------------------------------

def test_overlay_image_rescales_on_panel_resize(qtbot):
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

    assert (resized_size.width(), resized_size.height()) != (
        original_size.width(),
        original_size.height(),
    )
    original_ratio = original_size.width() / original_size.height()
    resized_ratio = resized_size.width() / resized_size.height()
    assert original_ratio == pytest.approx(resized_ratio, rel=0.05)
