from __future__ import annotations

import json
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from drawing_coach import perf
from drawing_coach.memory_store import MemoryStore
from drawing_coach.paths import sessions_dir


class ProgressPanel(QDialog):
    def __init__(
        self, memory_store: MemoryStore, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        perf.track(self)
        self.setWindowTitle("Progress")
        self.setMinimumSize(480, 480)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Recurring themes:"))
        self._theme_list = QListWidget()
        layout.addWidget(self._theme_list, 1)

        layout.addWidget(QLabel("Session timeline:"))
        self._session_list = QListWidget()
        layout.addWidget(self._session_list, 1)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close_btn)
        layout.addLayout(row)

        self._populate_themes(memory_store)
        self._populate_sessions()

    # ------------------------------------------------------------------

    def _populate_themes(self, memory_store: MemoryStore) -> None:
        observations = memory_store.observations()
        if not observations:
            self._theme_list.addItem(
                "No progress data yet — start drawing and getting feedback!"
            )
            return

        by_category: dict[str, set[str]] = {}
        counts: dict[str, int] = {}
        for obs in observations:
            counts[obs.category] = counts.get(obs.category, 0) + 1
            by_category.setdefault(obs.category, set()).add(obs.session_id)

        for category in sorted(counts, key=lambda c: -counts[c]):
            n = counts[category]
            sessions = len(by_category[category])
            self._theme_list.addItem(
                f"{category}: {n} observation{'s' if n != 1 else ''} across"
                f" {sessions} session{'s' if sessions != 1 else ''}"
            )

    def _populate_sessions(self) -> None:
        sd = sessions_dir()
        if not sd.exists():
            self._session_list.addItem("No sessions recorded yet")
            return

        starts: list[datetime] = []
        for candidate in sd.iterdir():
            meta_path = candidate / "meta.json"
            if not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text())
                starts.append(datetime.fromisoformat(meta["start_time"]))
            except Exception:
                continue

        if not starts:
            self._session_list.addItem("No sessions recorded yet")
            return

        for start in sorted(starts, reverse=True):
            self._session_list.addItem(start.strftime("%d %b %Y, %H:%M"))
