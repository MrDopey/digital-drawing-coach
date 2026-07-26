"""Unit tests for session name read/write helpers and session listing."""

import json
from datetime import datetime

from drawing_coach.session_manager import (
    default_session_name,
    delete_session,
    list_sessions,
    read_session_name,
    write_session_name,
)


def _write_meta(session_dir, **fields):
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "meta.json").write_text(json.dumps(fields))


# ---------------------------------------------------------------------------
# default_session_name
# ---------------------------------------------------------------------------

def test_default_session_name_with_app():
    ts = datetime(2026, 6, 14, 9, 41, 0)
    assert default_session_name(ts, "Krita") == "2026-06-14-09-41-00 | Krita"


def test_default_session_name_without_app():
    ts = datetime(2026, 6, 14, 9, 41, 0)
    assert default_session_name(ts, "") == "2026-06-14-09-41-00"


# ---------------------------------------------------------------------------
# read_session_name
# ---------------------------------------------------------------------------

def test_read_session_name_present(tmp_path):
    session_dir = tmp_path / "s1"
    _write_meta(session_dir, name="My Landscape Study", start_time="2026-06-14T09:41:00")
    assert read_session_name(session_dir) == "My Landscape Study"


def test_read_session_name_absent_falls_back_to_default(tmp_path):
    session_dir = tmp_path / "s2"
    _write_meta(session_dir, start_time="2026-06-14T09:41:00", drawing_app="Krita")
    assert read_session_name(session_dir) == "2026-06-14-09-41-00 | Krita"


def test_read_session_name_no_meta_file(tmp_path):
    session_dir = tmp_path / "s3"
    session_dir.mkdir()
    # Falls back to parsing the directory name as a timestamp.
    assert read_session_name(session_dir) != ""


# ---------------------------------------------------------------------------
# write_session_name
# ---------------------------------------------------------------------------

def test_write_session_name_sets_name(tmp_path):
    session_dir = tmp_path / "s4"
    _write_meta(session_dir, start_time="2026-06-14T09:41:00")
    write_session_name(session_dir, "Custom Name")
    meta = json.loads((session_dir / "meta.json").read_text())
    assert meta["name"] == "Custom Name"


def test_write_session_name_empty_clears_name(tmp_path):
    session_dir = tmp_path / "s5"
    _write_meta(session_dir, name="Old Name", start_time="2026-06-14T09:41:00")
    write_session_name(session_dir, "")
    meta = json.loads((session_dir / "meta.json").read_text())
    assert "name" not in meta


def test_write_session_name_strips_whitespace(tmp_path):
    session_dir = tmp_path / "s6"
    _write_meta(session_dir, start_time="2026-06-14T09:41:00")
    write_session_name(session_dir, "  Padded  ")
    meta = json.loads((session_dir / "meta.json").read_text())
    assert meta["name"] == "Padded"


# ---------------------------------------------------------------------------
# list_sessions / delete_session
# ---------------------------------------------------------------------------

def test_list_sessions_empty_dir(tmp_path):
    assert list_sessions(tmp_path) == []


def test_list_sessions_reverse_chronological(tmp_path):
    _write_meta(tmp_path / "a", start_time="2026-06-14T09:00:00")
    _write_meta(tmp_path / "b", start_time="2026-06-14T11:00:00")
    _write_meta(tmp_path / "c", start_time="2026-06-14T10:00:00")
    infos = list_sessions(tmp_path)
    assert [i.path.name for i in infos] == ["b", "c", "a"]


def test_list_sessions_skips_dirs_without_meta(tmp_path):
    (tmp_path / "no_meta").mkdir()
    _write_meta(tmp_path / "with_meta", start_time="2026-06-14T09:00:00")
    infos = list_sessions(tmp_path)
    assert [i.path.name for i in infos] == ["with_meta"]


def test_delete_session_removes_directory(tmp_path):
    session_dir = tmp_path / "to_delete"
    _write_meta(session_dir, start_time="2026-06-14T09:00:00")
    assert session_dir.exists()
    delete_session(session_dir)
    assert not session_dir.exists()
