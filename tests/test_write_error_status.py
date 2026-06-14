"""pytest-qt tests for the write-failure status bar label."""

from pathlib import Path

import pytest

from drawing_coach.main_window import _WriteErrorLabel


@pytest.fixture()
def label(qtbot):
    w = _WriteErrorLabel()
    qtbot.addWidget(w)
    return w


def test_label_empty_on_init(label):
    assert label.text() == ""


def test_set_error_shows_warning_text(label):
    path = Path("/some/session/frames/001.png")
    label.set_error(path, OSError("disk full"))
    assert "images will be lost" in label.text()
    assert "⚠" in label.text()


def test_set_error_updates_popup_body(label):
    path = Path("/some/session/frames/001.png")
    exc = OSError("permission denied")
    label.set_error(path, exc)
    popup_text = label._popup._text.toPlainText()
    assert str(path) in popup_text
    assert str(path.parent) in popup_text
    assert "permission denied" in popup_text


def test_clear_error_empties_label(label):
    label.set_error(Path("/tmp/frames/001.png"), OSError("disk full"))
    assert label.text() != ""
    label.clear_error()
    assert label.text() == ""


def test_clear_error_hides_popup(label):
    label.set_error(Path("/tmp/frames/001.png"), OSError("disk full"))
    label._popup.show()
    label.clear_error()
    assert not label._popup.isVisible()
