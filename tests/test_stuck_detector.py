"""Unit tests for StuckDetector MAE logic."""

from datetime import datetime

import numpy as np
from PIL import Image

from drawing_coach.capture_engine import CapturedFrame
from drawing_coach.stuck_detector import StuckDetector


def _frame(array: np.ndarray) -> CapturedFrame:
    img = Image.fromarray(array.astype(np.uint8))
    return CapturedFrame(image=img, timestamp=datetime.now())


def _solid(value: int, size: int = 64) -> np.ndarray:
    return np.full((size, size), value, dtype=np.uint8)


def test_no_trigger_on_first_frame():
    detector = StuckDetector(threshold=5.0, consecutive_count=2, cooldown_seconds=0)
    fired = []
    detector.on_stuck = lambda: fired.append(1)

    detector.feed(_frame(_solid(100)))
    assert not fired


def test_identical_frames_trigger_after_consecutive_count():
    detector = StuckDetector(threshold=5.0, consecutive_count=2, cooldown_seconds=0)
    fired = []
    detector.on_stuck = lambda: fired.append(1)

    f = _frame(_solid(128))
    detector.feed(f)  # sets last_frame
    detector.feed(f)  # consecutive=1
    assert not fired
    detector.feed(f)  # consecutive=2 → trigger
    assert len(fired) == 1


def test_different_frames_do_not_trigger():
    detector = StuckDetector(threshold=5.0, consecutive_count=2, cooldown_seconds=0)
    fired = []
    detector.on_stuck = lambda: fired.append(1)

    detector.feed(_frame(_solid(0)))
    detector.feed(_frame(_solid(100)))  # high MAE → resets consecutive
    detector.feed(_frame(_solid(200)))
    assert not fired


def test_cooldown_blocks_retrigger():
    detector = StuckDetector(threshold=5.0, consecutive_count=1, cooldown_seconds=9999)
    fired = []
    detector.on_stuck = lambda: fired.append(1)

    f = _frame(_solid(50))
    detector.feed(f)
    detector.feed(f)  # trigger 1
    detector.feed(f)  # should be blocked by cooldown
    detector.feed(f)
    assert len(fired) == 1


def test_manual_trigger_bypasses_cooldown():
    detector = StuckDetector(threshold=5.0, consecutive_count=1, cooldown_seconds=9999)
    fired = []
    detector.on_stuck = lambda: fired.append(1)

    f = _frame(_solid(50))
    detector.feed(f)
    detector.feed(f)  # first trigger
    assert len(fired) == 1

    detector.manual_trigger()  # should fire despite cooldown
    assert len(fired) == 2


def test_mae_computation():
    a = _frame(_solid(0))
    b = _frame(_solid(50))
    mae = StuckDetector._compute_mae(a.image, b.image)
    assert abs(mae - 50.0) < 1.0
