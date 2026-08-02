"""Unit tests for drawing_coach.memory_store.MemoryStore."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from drawing_coach.llm_config import LLMConfig
from drawing_coach.memory_store import MemoryStore, Observation


def _mock_response(text: str):
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def paths(tmp_path):
    mem = tmp_path / "memory.json"
    summ = tmp_path / "memory_summaries.json"
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    with (
        patch("drawing_coach.memory_store.memory_path", return_value=mem),
        patch("drawing_coach.memory_store.memory_summaries_path", return_value=summ),
        patch("drawing_coach.memory_store.sessions_dir", return_value=sessions),
    ):
        yield mem, summ, sessions


def _obs(category="perspective", note="note", session_id="s1", date=None):
    # Summary.date is stamped with the real datetime.now() at resummarisation
    # time, so observations meant to land "after" a summary must use real
    # timestamps too, rather than a canned fixed date, to preserve ordering.
    return Observation(
        date=date or datetime.now().isoformat(),
        session_id=session_id,
        category=category,
        note=note,
    )


# ------------------------------------------------------------------
# 5.1 append
# ------------------------------------------------------------------


def test_append_normal(paths):
    store = MemoryStore(LLMConfig())
    store.append(_obs())
    assert len(store.observations()) == 1


def test_append_cap_overflow_default(paths):
    store = MemoryStore(LLMConfig(memory_max_observations=3))
    for i in range(5):
        store.append(_obs(note=f"note{i}"))
    obs = store.observations()
    assert len(obs) == 3
    assert obs[-1].note == "note4"


def test_append_custom_cap(paths):
    store = MemoryStore(LLMConfig(memory_max_observations=1))
    store.append(_obs(note="first"))
    store.append(_obs(note="second"))
    obs = store.observations()
    assert len(obs) == 1
    assert obs[0].note == "second"


def test_append_save_round_trip(paths):
    mem, _, _ = paths
    store = MemoryStore(LLMConfig())
    store.append(_obs(note="persisted"))

    reloaded = MemoryStore(LLMConfig())
    assert len(reloaded.observations()) == 1
    assert reloaded.observations()[0].note == "persisted"
    assert json.loads(mem.read_text())["observations"][0]["note"] == "persisted"


# ------------------------------------------------------------------
# append_observations (structured-output path)
# ------------------------------------------------------------------


def test_append_observations_normal(paths):
    store = MemoryStore(LLMConfig())
    store.append_observations(
        [{"category": "perspective", "note": "vanishing points"}], "session-1"
    )
    obs = store.observations()
    assert len(obs) == 1
    assert obs[0].category == "perspective"
    assert obs[0].note == "vanishing points"
    assert obs[0].session_id == "session-1"


def test_append_observations_cap_matches_append(paths):
    store = MemoryStore(LLMConfig(memory_max_observations=3))
    store.append_observations(
        [{"category": "c", "note": f"n{i}"} for i in range(5)], "session-1"
    )
    obs = store.observations()
    assert len(obs) == 3
    assert obs[-1].note == "n4"


def test_append_observations_empty_list_no_op(paths):
    store = MemoryStore(LLMConfig())
    store.append_observations([], "session-1")
    assert store.observations() == []


def test_append_observations_skips_malformed_items(paths):
    store = MemoryStore(LLMConfig())
    store.append_observations(
        [{"category": "perspective"}, {"note": "missing category"}, {}], "session-1"
    )
    assert store.observations() == []


# ------------------------------------------------------------------
# 5.2 extract_and_append
# ------------------------------------------------------------------


def test_extract_and_append_valid_comment(paths):
    store = MemoryStore(LLMConfig())
    text = (
        "Great work on the shading.\n"
        "<!-- observations: "
        '[{"category": "perspective", "note": "vanishing points"}] -->'
    )
    result = store.extract_and_append(text, "session-1")
    assert "observations:" not in result
    assert "Great work on the shading." in result
    obs = store.observations()
    assert len(obs) == 1
    assert obs[0].category == "perspective"
    assert obs[0].note == "vanishing points"
    assert obs[0].session_id == "session-1"


def test_extract_and_append_comment_absent(paths):
    store = MemoryStore(LLMConfig())
    text = "Just plain feedback with no comment."
    result = store.extract_and_append(text, "session-1")
    assert result == text
    assert store.observations() == []


def test_extract_and_append_malformed_comment(paths):
    store = MemoryStore(LLMConfig())
    text = "Feedback text.\n<!-- observations: {not valid json ] -->"
    result = store.extract_and_append(text, "session-1")
    assert "observations:" not in result
    assert store.observations() == []


# ------------------------------------------------------------------
# 5.3 summarise
# ------------------------------------------------------------------


def test_summarise_empty(paths):
    store = MemoryStore(LLMConfig())
    assert store.summarise() == ""


def test_summarise_non_empty(paths):
    store = MemoryStore(LLMConfig(memory_resummarize_interval=0))
    store.append(_obs(note="struggles with hands"))
    result = store.summarise()
    assert "struggles with hands" in result
    assert "sessions" in result


def test_summarise_more_than_20_observations(paths):
    store = MemoryStore(LLMConfig(memory_resummarize_interval=0))
    for i in range(25):
        store.append(_obs(note=f"note{i}"))
    result = store.summarise(max_obs=20)
    assert "note24" in result
    assert "note4" not in result  # pruned from the shown window (oldest of the 25)


# ------------------------------------------------------------------
# 5.5 re-summarisation
# ------------------------------------------------------------------


def test_resummarize_default_triggers_at_threshold(paths):
    store = MemoryStore(LLMConfig(model="gpt-4o", memory_resummarize_interval=3))
    with patch(
        "litellm.completion", return_value=_mock_response("Condensed summary.")
    ) as mock_completion:
        for i in range(3):
            store.append(_obs(note=f"note{i}"))
        store.summarise()
    mock_completion.assert_called_once()
    assert len(store.summaries()) == 1
    assert store.summaries()[0].text == "Condensed summary."


def test_resummarize_zero_never_triggers(paths):
    store = MemoryStore(LLMConfig(model="gpt-4o", memory_resummarize_interval=0))
    with patch("litellm.completion") as mock_completion:
        for i in range(50):
            store.append(_obs(note=f"note{i}"))
        store.summarise()
    mock_completion.assert_not_called()
    assert store.summaries() == []


def test_resummarize_resets_counter(paths):
    store = MemoryStore(LLMConfig(model="gpt-4o", memory_resummarize_interval=2))
    with patch("litellm.completion", return_value=_mock_response("Summary A.")):
        store.append(_obs(note="a"))
        store.append(_obs(note="b"))
        store.summarise()  # triggers resummarization, resets counter

    with patch(
        "litellm.completion", return_value=_mock_response("Summary B.")
    ) as mock_completion:
        store.append(_obs(note="c"))
        store.summarise()  # only 1 appended since reset — should not trigger yet
        mock_completion.assert_not_called()
        store.append(_obs(note="d"))
        store.summarise()  # now 2 appended since reset — triggers
        mock_completion.assert_called_once()

    assert len(store.summaries()) == 2


def test_resummarize_failure_falls_back(paths):
    store = MemoryStore(LLMConfig(model="gpt-4o", memory_resummarize_interval=1))
    with patch("litellm.completion", side_effect=RuntimeError("boom")):
        store.append(_obs(note="a"))
        result = store.summarise()

    assert store.summaries() == []
    assert "a" in result or "note" not in result  # falls back to raw notes, no crash


# ------------------------------------------------------------------
# 5.6 summaries history
# ------------------------------------------------------------------


def test_condensation_appends_not_overwrites(paths):
    store = MemoryStore(LLMConfig(model="gpt-4o", memory_resummarize_interval=1))
    with patch("litellm.completion", return_value=_mock_response("First.")):
        store.append(_obs(note="a"))
        store.summarise()
    with patch("litellm.completion", return_value=_mock_response("Second.")):
        store.append(_obs(note="b"))
        store.summarise()

    summaries = store.summaries()
    assert len(summaries) == 2
    assert summaries[0].text == "First."
    assert summaries[1].text == "Second."


def test_summary_history_cap_overflow_prunes_oldest(paths):
    store = MemoryStore(
        LLMConfig(
            model="gpt-4o", memory_resummarize_interval=1, memory_summary_history_max=2
        )
    )
    for i in range(4):
        with patch("litellm.completion", return_value=_mock_response(f"Summary{i}.")):
            store.append(_obs(note=f"n{i}"))
            store.summarise()

    summaries = store.summaries()
    assert len(summaries) == 2
    assert summaries[-1].text == "Summary3."


def test_summarise_uses_only_most_recent_summary(paths):
    store = MemoryStore(LLMConfig(model="gpt-4o", memory_resummarize_interval=1))
    with patch("litellm.completion", return_value=_mock_response("Old summary.")):
        store.append(_obs(note="a"))
        store.summarise()
    with patch("litellm.completion", return_value=_mock_response("New summary.")):
        store.append(_obs(note="b"))
        store.summarise()

    with patch("litellm.completion") as mock_completion:
        result = store.summarise()
    mock_completion.assert_not_called()
    assert "New summary." in result
    assert "Old summary." not in result


# ------------------------------------------------------------------
# 5.7 two-file split
# ------------------------------------------------------------------


def test_files_load_independently_when_one_missing(paths):
    mem, summ, _ = paths
    store = MemoryStore(LLMConfig())
    store.append(_obs(note="only observations"))
    assert mem.exists()
    assert not summ.exists()

    reloaded = MemoryStore(LLMConfig())
    assert len(reloaded.observations()) == 1
    assert reloaded.summaries() == []


def test_files_load_independently_when_malformed(paths):
    mem, summ, _ = paths
    mem.write_text("not valid json")
    summ.write_text("{}")
    store = MemoryStore(LLMConfig())
    assert store.observations() == []
    assert store.summaries() == []


def test_append_only_rewrites_observations_file(paths):
    mem, summ, _ = paths
    store = MemoryStore(LLMConfig())
    store.append(_obs())
    assert mem.exists()
    assert not summ.exists()


def test_append_summary_only_rewrites_summaries_file(paths):
    mem, summ, _ = paths
    store = MemoryStore(LLMConfig(model="gpt-4o", memory_resummarize_interval=1))
    before_mtime = None
    with patch("litellm.completion", return_value=_mock_response("Summary.")):
        store.append(_obs(note="a"))
        before_mtime = mem.stat().st_mtime
        store.summarise()

    assert summ.exists()
    assert mem.stat().st_mtime == before_mtime


def test_clear_resets_both_files_and_counter(paths):
    store = MemoryStore(LLMConfig(model="gpt-4o", memory_resummarize_interval=1))
    with patch("litellm.completion", return_value=_mock_response("Summary.")):
        store.append(_obs())
        store.summarise()

    store.clear()
    assert store.observations() == []
    assert store.summaries() == []
    assert store.summarise() == ""

    reloaded = MemoryStore(LLMConfig())
    assert reloaded.observations() == []
    assert reloaded.summaries() == []
