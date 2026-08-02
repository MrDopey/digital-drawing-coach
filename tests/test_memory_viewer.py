"""Tests that the Memory Viewer's coach's-notes preview is strictly read-only:
opening it, or refreshing it after a delete or clear-all, never triggers
re-summarisation."""

from datetime import datetime
from unittest.mock import patch

from drawing_coach.llm_config import LLMConfig
from drawing_coach.memory_store import MemoryStore, Observation
from drawing_coach.memory_viewer import MemoryViewerDialog


def _obs(category="perspective", note="note", session_id="s1"):
    return Observation(
        date=datetime.now().isoformat(),
        session_id=session_id,
        category=category,
        note=note,
    )


def _store(tmp_path, **config_kwargs):
    mem = tmp_path / "memory.json"
    summ = tmp_path / "memory_summaries.json"
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    with (
        patch("drawing_coach.memory_store.memory_path", return_value=mem),
        patch("drawing_coach.memory_store.memory_summaries_path", return_value=summ),
        patch("drawing_coach.memory_store.sessions_dir", return_value=sessions),
    ):
        store = MemoryStore(LLMConfig(**config_kwargs))
    return store, mem, summ


def _dialog(qtbot, store: MemoryStore) -> MemoryViewerDialog:
    dlg = MemoryViewerDialog(store)
    qtbot.addWidget(dlg)
    return dlg


def test_opening_viewer_never_triggers_resummarize(qtbot, tmp_path):
    store, _, summ = _store(
        tmp_path, model="gpt-4o", memory_resummarize_interval=1
    )
    store.append(_obs(note="crosses the threshold"))

    with patch("litellm.completion") as mock_completion:
        dlg = _dialog(qtbot, store)

    mock_completion.assert_not_called()
    assert not summ.exists()
    assert "crosses the threshold" in dlg._notes_view.toPlainText()


def test_refresh_after_delete_stays_read_only(qtbot, tmp_path):
    store, _, summ = _store(
        tmp_path, model="gpt-4o", memory_resummarize_interval=1
    )
    store.append(_obs(note="one"))
    dlg = _dialog(qtbot, store)

    with patch("litellm.completion") as mock_completion:
        dlg._delete(0)

    mock_completion.assert_not_called()
    assert not summ.exists()


def test_refresh_after_clear_all_stays_read_only(qtbot, tmp_path):
    store, _, summ = _store(
        tmp_path, model="gpt-4o", memory_resummarize_interval=1
    )
    store.append(_obs(note="one"))
    dlg = _dialog(qtbot, store)

    with patch("litellm.completion") as mock_completion:
        store.clear()
        dlg._refresh()

    mock_completion.assert_not_called()
    assert not summ.exists()
    assert dlg._notes_view.toPlainText() == "No coach's notes yet."
