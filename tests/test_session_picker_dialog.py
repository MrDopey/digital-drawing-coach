"""pytest-qt tests for SessionPickerDialog."""

import json
from unittest.mock import patch

from PyQt6.QtWidgets import QMessageBox

from drawing_coach.session_picker_dialog import SessionPickerDialog


def _write_meta(session_dir, **fields):
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "meta.json").write_text(json.dumps(fields))


def test_choose_session_skips_dialog_when_empty(tmp_path):
    with patch("drawing_coach.session_manager.sessions_dir", return_value=tmp_path):
        action, session_dir = SessionPickerDialog.choose_session()
    assert action == "new"
    assert session_dir is None


def test_dialog_lists_sessions_reverse_chronological(qtbot, tmp_path):
    _write_meta(tmp_path / "a", start_time="2026-06-14T09:00:00", name="Older")
    _write_meta(tmp_path / "b", start_time="2026-06-14T11:00:00", name="Newer")

    with patch("drawing_coach.session_manager.sessions_dir", return_value=tmp_path):
        dlg = SessionPickerDialog()
    qtbot.addWidget(dlg)

    names = [row.info.name for row in dlg._rows]
    assert names == ["Newer", "Older"]


def test_resume_returns_selected_session_path(qtbot, tmp_path):
    session_dir = tmp_path / "a"
    _write_meta(session_dir, start_time="2026-06-14T09:00:00", name="Only")

    with patch("drawing_coach.session_manager.sessions_dir", return_value=tmp_path):
        dlg = SessionPickerDialog()
    qtbot.addWidget(dlg)

    dlg._resume()
    assert dlg.result_action == "resume"
    assert dlg.result_session == session_dir


def test_new_session_button_returns_new(qtbot, tmp_path):
    _write_meta(tmp_path / "a", start_time="2026-06-14T09:00:00")

    with patch("drawing_coach.session_manager.sessions_dir", return_value=tmp_path):
        dlg = SessionPickerDialog()
    qtbot.addWidget(dlg)

    dlg._new()
    assert dlg.result_action == "new"
    assert dlg.result_session is None


def test_reject_returns_quit(qtbot, tmp_path):
    _write_meta(tmp_path / "a", start_time="2026-06-14T09:00:00")

    with patch("drawing_coach.session_manager.sessions_dir", return_value=tmp_path):
        dlg = SessionPickerDialog()
    qtbot.addWidget(dlg)

    dlg.reject()
    assert dlg.result_action == "quit"
    assert dlg.result_session is None


def test_delete_removes_session_from_disk_and_list(qtbot, tmp_path):
    session_dir = tmp_path / "a"
    _write_meta(session_dir, start_time="2026-06-14T09:00:00")

    with patch("drawing_coach.session_manager.sessions_dir", return_value=tmp_path):
        dlg = SessionPickerDialog()
    qtbot.addWidget(dlg)

    with patch.object(
        QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes
    ):
        dlg._delete()

    assert not session_dir.exists()
    assert dlg._rows == []


def test_rename_via_editable_label_persists(qtbot, tmp_path):
    session_dir = tmp_path / "a"
    _write_meta(session_dir, start_time="2026-06-14T09:00:00", name="Original")

    with patch("drawing_coach.session_manager.sessions_dir", return_value=tmp_path):
        dlg = SessionPickerDialog()
    qtbot.addWidget(dlg)

    row = dlg._rows[0]
    row._name_label.start_edit()
    row._name_label._edit.setText("Renamed")
    row._name_label._commit()

    meta = json.loads((session_dir / "meta.json").read_text())
    assert meta["name"] == "Renamed"
    assert row.info.name == "Renamed"
