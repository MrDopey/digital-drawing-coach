from __future__ import annotations

from pathlib import Path

from drawing_coach.feedback_engine import FeedbackResponse
from drawing_coach.paths import feedback_dir


class FeedbackStore:
    """Disk persistence for `FeedbackResponse` entries within one session."""

    def __init__(self, session_dir: Path) -> None:
        self._dir = feedback_dir(session_dir)

    def _stem(self, response: FeedbackResponse) -> str:
        return f"{response.timestamp.strftime('%Y%m%d_%H%M%S')}_{response.mode}"
