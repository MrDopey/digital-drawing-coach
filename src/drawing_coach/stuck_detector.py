from __future__ import annotations

import time
from typing import Callable

import numpy as np
from PIL import Image

from drawing_coach.capture_engine import CapturedFrame


class StuckDetector:
    """Compares consecutive frames via MAE to detect drawing inactivity."""

    def __init__(
        self,
        threshold: float = 10.0,
        consecutive_count: int = 3,
        cooldown_seconds: int = 300,
    ) -> None:
        self.threshold = threshold
        self.consecutive_count = consecutive_count
        self.cooldown_seconds = cooldown_seconds

        self._consecutive: int = 0
        self._last_trigger: float = 0.0
        self._last_frame: Image.Image | None = None
        self.on_stuck: Callable[[], None] | None = None

    def feed(self, frame: CapturedFrame) -> None:
        """Call with each new frame. Fires on_stuck when stuck is detected."""
        if self._last_frame is None:
            self._last_frame = frame.image
            return

        mae = self._compute_mae(self._last_frame, frame.image)
        self._last_frame = frame.image

        if mae < self.threshold:
            self._consecutive += 1
            if self._consecutive >= self.consecutive_count:
                self._maybe_trigger()
        else:
            self._consecutive = 0

    def is_in_cooldown(self) -> bool:
        return (time.monotonic() - self._last_trigger) < self.cooldown_seconds

    def manual_trigger(self) -> None:
        """Bypass cooldown and fire immediately; resets cooldown timer."""
        self._last_trigger = time.monotonic()
        if self.on_stuck:
            self.on_stuck()

    def reset_cooldown(self) -> None:
        self._last_trigger = time.monotonic()

    # ------------------------------------------------------------------

    def _maybe_trigger(self) -> None:
        if self.is_in_cooldown():
            return
        self._last_trigger = time.monotonic()
        self._consecutive = 0
        if self.on_stuck:
            self.on_stuck()

    @staticmethod
    def _compute_mae(a: Image.Image, b: Image.Image) -> float:
        arr_a = np.asarray(a.convert("L"), dtype=np.float32)
        arr_b = np.asarray(b.resize(a.size).convert("L"), dtype=np.float32)
        return float(np.mean(np.abs(arr_a - arr_b)))
