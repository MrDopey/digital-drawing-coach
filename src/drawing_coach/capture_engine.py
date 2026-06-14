from __future__ import annotations

import json
import logging
import shutil
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import mss
import numpy as np
from PIL import Image

from drawing_coach.paths import sessions_dir
from drawing_coach.window_manager import WindowInfo, WindowManager

if TYPE_CHECKING:
    from drawing_coach.llm_config import LLMConfig

_log = logging.getLogger("drawing_coach.capture_engine")
_SESSION_RESUME_HOURS = 24


@dataclass
class CapturedFrame:
    image: Image.Image
    timestamp: datetime = field(default_factory=datetime.now)
    path: Path | None = None  # disk path, None for in-memory only


class CaptureEngine:
    """Captures the drawing window periodically; stores frames to disk with dedup."""

    DEFAULT_INTERVAL = 30
    BUFFER_SIZE = 50

    def __init__(self, manager: WindowManager, config: LLMConfig | None = None) -> None:
        self._manager = manager
        self._config = config  # LLMConfig reference for live thresholds
        self._target: WindowInfo | None = None
        self._buffer: deque[CapturedFrame] = deque(maxlen=self.BUFFER_SIZE)
        self._interval: int = self.DEFAULT_INTERVAL
        self._paused: bool = False
        self._running: bool = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

        self._session_dir: Path | None = None
        self._frame_count: int = 0
        self._last_stored_image: Image.Image | None = None

        self.on_frame_captured: Callable[[CapturedFrame], None] | None = None
        self.on_window_lost: Callable[[], None] | None = None
        self.on_write_error: Callable[[Path, Exception], None] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def target(self) -> WindowInfo | None:
        return self._target

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def interval(self) -> int:
        return self._interval

    @interval.setter
    def interval(self, seconds: int) -> None:
        self._interval = max(5, min(300, seconds))

    def set_target(self, window: WindowInfo) -> None:
        self._target = window
        if self._session_dir:
            self._write_meta()

    def get_frames(self) -> list[CapturedFrame]:
        with self._lock:
            return list(self._buffer)

    def start(self) -> None:
        if self._running:
            return
        self._init_session()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def pause(self) -> None:
        self._paused = True
        _log.info("Capture paused by user")

    def resume(self) -> None:
        self._paused = False
        _log.info("Capture resumed")

    def capture_once(self) -> CapturedFrame | None:
        return self._do_capture()

    def apply_retention(self, keep: int) -> None:
        """Delete oldest session directories until only `keep` remain."""
        self._cleanup_old_sessions(keep)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _init_session(self) -> None:
        sd = sessions_dir()
        sd.mkdir(parents=True, exist_ok=True)
        self._cleanup_old_sessions(
            self._config.history_retention_sessions if self._config else 10
        )

        # Try to resume the most recent session if < 24 hours old
        existing = sorted(sd.iterdir()) if sd.exists() else []
        for candidate in reversed(existing):
            meta_path = candidate / "meta.json"
            if not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text())
                start = datetime.fromisoformat(meta["start_time"])
                if datetime.now() - start < timedelta(hours=_SESSION_RESUME_HOURS):
                    self._session_dir = candidate
                    self._load_frames_from_disk()
                    n = len(self._buffer)
                    _log.info("Resumed session: %s (%d existing frames)", candidate, n)
                    return
            except Exception:
                continue

        # Start a new session
        session_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        self._session_dir = sessions_dir() / session_id
        (self._session_dir / "frames").mkdir(parents=True)
        self._write_meta()
        _log.info("New session: %s", self._session_dir)

    def _write_meta(self) -> None:
        if not self._session_dir:
            return
        meta = {
            "start_time": datetime.now().isoformat(),
            "drawing_app": self._target.app_name if self._target else "",
            "style_focus": self._config.style_focus if self._config else "",
        }
        (self._session_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    def _load_frames_from_disk(self) -> None:
        if not self._session_dir:
            return
        frames_dir = self._session_dir / "frames"
        loaded: list[CapturedFrame] = []
        for png in sorted(frames_dir.glob("*.png")):
            try:
                img = Image.open(png).copy()
                ts_str = png.stem.split("_")[0]
                ts = datetime.strptime(ts_str, "%H%M%S")
                ts = ts.replace(
                    year=datetime.now().year,
                    month=datetime.now().month,
                    day=datetime.now().day,
                )
                loaded.append(CapturedFrame(image=img, timestamp=ts, path=png))
            except Exception:
                continue
        with self._lock:
            self._buffer = deque(loaded, maxlen=self.BUFFER_SIZE)
            self._frame_count = len(loaded)
        if loaded:
            self._last_stored_image = loaded[-1].image

    @staticmethod
    def _cleanup_old_sessions(keep: int) -> None:
        sd = sessions_dir()
        if not sd.exists():
            return
        sessions = sorted(sd.iterdir())
        to_delete = sessions[: max(0, len(sessions) - keep)]
        for old in to_delete:
            try:
                shutil.rmtree(old)
            except Exception:
                pass
        if to_delete:
            _log.info("Pruned %d old sessions (retention: %d)", len(to_delete), keep)

    # ------------------------------------------------------------------
    # Capture loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        next_tick = time.monotonic() + self._interval
        while self._running:
            now = time.monotonic()
            if now >= next_tick:
                if not self._paused:
                    self._do_capture()
                next_tick = time.monotonic() + self._interval
            time.sleep(0.5)

    def _do_capture(self) -> CapturedFrame | None:
        if self._target is None:
            return None
        rect = self._manager.get_window_rect(self._target.id)
        if rect is None:
            _log.warning("Drawing window lost — capture paused")
            if self.on_window_lost:
                self.on_window_lost()
            return None

        left, top, width, height = rect
        if width <= 0 or height <= 0:
            return None

        with mss.mss() as sct:
            shot = sct.grab(
                {"left": left, "top": top, "width": width, "height": height}
            )
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

        # Dedup check
        dedup_threshold = self._config.dedup_threshold if self._config else 2.0
        if self._last_stored_image is not None:
            mae = _compute_mae(self._last_stored_image, img)
            if mae < dedup_threshold:
                _log.debug("Frame skipped: MAE=%.2f < threshold=%.2f", mae, dedup_threshold)
                return None  # duplicate — discard

        # Write to disk
        frame_path = self._write_frame(img)
        frame = CapturedFrame(image=img, timestamp=datetime.now(), path=frame_path)
        self._last_stored_image = img

        with self._lock:
            self._buffer.append(frame)

        if self.on_frame_captured:
            self.on_frame_captured(frame)
        return frame

    def _write_frame(self, img: Image.Image) -> Path | None:
        if not self._session_dir:
            return None
        self._frame_count += 1
        ts = datetime.now().strftime("%H%M%S")
        filename = f"{ts}_{self._frame_count:04d}.png"
        path = self._session_dir / "frames" / filename
        try:
            img.save(path, format="PNG")
            _log.debug("Frame saved: %s (%dx%d)", filename, img.width, img.height)
            return path
        except Exception as exc:
            _log.warning("Frame write failed: %s", path, exc_info=True)
            if self.on_write_error:
                self.on_write_error(path, exc)
            return None


def _compute_mae(a: Image.Image, b: Image.Image) -> float:
    arr_a = np.asarray(a.convert("L"), dtype=np.float32)
    arr_b = np.asarray(b.resize(a.size).convert("L"), dtype=np.float32)
    return float(np.mean(np.abs(arr_a - arr_b)))
