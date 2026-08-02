from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import litellm

from drawing_coach.llm_config import LLMConfig
from drawing_coach.paths import memory_path, memory_summaries_path, sessions_dir

_log = logging.getLogger("drawing_coach.memory_store")

_OBSERVATIONS_RE = re.compile(r"<!--\s*observations:\s*(.*?)\s*-->", re.DOTALL)

_RESUMMARIZE_SYSTEM_PROMPT = (
    "You are condensing a running log of an art coach's observations about a "
    "student into a compact summary for future reference. Preserve recurring "
    "themes and specific, actionable detail; drop redundancy. Return prose only, "
    "with no preamble or headers."
)


@dataclass
class Observation:
    date: str
    session_id: str
    category: str
    note: str


@dataclass
class Summary:
    date: str
    text: str
    observation_count: int


class MemoryStore:
    """Persists drawing observations (`memory.json`) and their periodic
    re-summarisation history (`memory_summaries.json`) across sessions."""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self._config = config or LLMConfig()
        self._observations: list[Observation] = self._load_observations()
        self._summaries, self._last_resummarized_count = self._load_summaries()

    # ------------------------------------------------------------------
    # Loading / saving
    # ------------------------------------------------------------------

    def _load_observations(self) -> list[Observation]:
        path = memory_path()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            return [Observation(**o) for o in data.get("observations", [])]
        except Exception:
            _log.debug(
                "memory.json malformed or unreadable, starting empty", exc_info=True
            )
            return []

    def _load_summaries(self) -> tuple[list[Summary], int]:
        path = memory_summaries_path()
        if not path.exists():
            return [], 0
        try:
            data = json.loads(path.read_text())
            summaries = [Summary(**s) for s in data.get("summaries", [])]
            count = int(data.get("last_resummarized_count", 0))
            return summaries, count
        except Exception:
            _log.debug(
                "memory_summaries.json malformed or unreadable, starting empty",
                exc_info=True,
            )
            return [], 0

    def _save_observations(self) -> None:
        path = memory_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"observations": [asdict(o) for o in self._observations]}
        path.write_text(json.dumps(data, indent=2))

    def _save_summaries(self) -> None:
        path = memory_summaries_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "summaries": [asdict(s) for s in self._summaries],
            "last_resummarized_count": self._last_resummarized_count,
        }
        path.write_text(json.dumps(data, indent=2))

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def observations(self) -> list[Observation]:
        return list(self._observations)

    def summaries(self) -> list[Summary]:
        return list(self._summaries)

    def append(self, obs: Observation) -> None:
        self._observations.append(obs)
        cap = max(1, self._config.memory_max_observations)
        if len(self._observations) > cap:
            self._observations = self._observations[-cap:]
        self._last_resummarized_count += 1
        self._save_observations()

    def append_observations(self, items: list[dict], session_id: str) -> None:
        """Append already-parsed `{category, note}` records (the structured-output
        path), reusing the same cap/prune logic as `append()`."""
        now = datetime.now().isoformat()
        for item in items:
            try:
                category = str(item["category"])
                note = str(item["note"])
            except (KeyError, TypeError):
                continue
            self.append(
                Observation(
                    date=now, session_id=session_id, category=category, note=note
                )
            )

    def delete(self, idx: int) -> None:
        del self._observations[idx]
        self._save_observations()

    def clear(self) -> None:
        self._observations = []
        self._summaries = []
        self._last_resummarized_count = 0
        self._save_observations()
        self._save_summaries()

    # ------------------------------------------------------------------
    # Extraction from LLM response text
    # ------------------------------------------------------------------

    def extract_and_append(self, response_text: str, session_id: str) -> str:
        match = _OBSERVATIONS_RE.search(response_text)
        if not match:
            return response_text

        stripped = (
            response_text[: match.start()] + response_text[match.end() :]
        ).strip()

        try:
            items = json.loads(match.group(1))
        except Exception:
            _log.debug("Malformed observations comment, ignoring", exc_info=True)
            return stripped

        now = datetime.now().isoformat()
        for item in items:
            try:
                category = str(item["category"])
                note = str(item["note"])
            except (KeyError, TypeError):
                continue
            self.append(
                Observation(
                    date=now, session_id=session_id, category=category, note=note
                )
            )

        return stripped

    # ------------------------------------------------------------------
    # Coach's notes / re-summarisation
    # ------------------------------------------------------------------

    def summarise(self, max_obs: int = 20) -> str:
        interval = self._config.memory_resummarize_interval
        if (
            interval > 0
            and self._last_resummarized_count >= interval
            and self._observations
        ):
            self._try_resummarize()

        return self._format_notes(max_obs)

    def current_notes(self, max_obs: int = 20) -> str:
        """Read-only preview of the coach's notes: formats already-persisted
        state without checking the re-summarisation threshold, calling the
        re-summarisation LLM, or writing to `memory_summaries.json`."""
        return self._format_notes(max_obs)

    def _format_notes(self, max_obs: int = 20) -> str:
        if not self._observations and not self._summaries:
            return ""

        sessions = self._session_count()
        lines = [f"You have worked with this student across {sessions} sessions."]

        if self._summaries:
            latest = self._summaries[-1]
            lines.append(latest.text)
            since = datetime.fromisoformat(latest.date)
            recent = [
                o for o in self._observations if datetime.fromisoformat(o.date) > since
            ][-max_obs:]
        else:
            recent = self._observations[-max_obs:]

        if recent:
            lines.append("Recent observations:")
            lines.extend(f"- {o.category}: {o.note}" for o in recent)

        return "\n".join(lines)

    def _session_count(self) -> int:
        sd = sessions_dir()
        if not sd.exists():
            return 0
        return sum(1 for p in sd.iterdir() if p.is_dir())

    def _try_resummarize(self) -> None:
        if self._summaries:
            since = datetime.fromisoformat(self._summaries[-1].date)
            raw_since = [
                o for o in self._observations if datetime.fromisoformat(o.date) > since
            ]
            prior_text = self._summaries[-1].text
            prior_count = self._summaries[-1].observation_count
        else:
            raw_since = list(self._observations)
            prior_text = ""
            prior_count = 0

        if not raw_since:
            self._last_resummarized_count = 0
            self._save_summaries()
            return

        bullets = "\n".join(f"- {o.category}: {o.note}" for o in raw_since)
        user_content = (
            f"Previous summary:\n{prior_text}\n\nNew observations:\n{bullets}"
            if prior_text
            else bullets
        )

        try:
            kwargs: dict[str, Any] = {
                "model": self._config.model,
                "messages": [
                    {"role": "system", "content": _RESUMMARIZE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "metadata": {"debug_label": "memory_resummarize"},
            }
            if self._config.api_key:
                kwargs["api_key"] = self._config.api_key
            if self._config.api_base:
                kwargs["api_base"] = self._config.api_base
            response = litellm.completion(**kwargs)
            text = (response.choices[0].message.content or "").strip()
            if not text:
                raise ValueError("empty re-summarisation response")
        except Exception:
            _log.debug(
                "Re-summarisation LLM call failed, keeping prior notes", exc_info=True
            )
            return

        summary = Summary(
            date=datetime.now().isoformat(),
            text=text,
            observation_count=prior_count + len(raw_since),
        )
        self._summaries.append(summary)
        cap = max(1, self._config.memory_summary_history_max)
        if len(self._summaries) > cap:
            self._summaries = self._summaries[-cap:]
        self._last_resummarized_count = 0
        self._save_summaries()
