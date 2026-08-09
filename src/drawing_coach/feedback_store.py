from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

from PIL import Image as PilImage

from drawing_coach.capture_engine import CapturedFrame
from drawing_coach.feedback_engine import FeedbackResponse
from drawing_coach.paths import feedback_dir

_log = logging.getLogger("drawing_coach.feedback_store")


class FeedbackStore:
    """Disk persistence for `FeedbackResponse` entries within one session."""

    def __init__(self, session_dir: Path) -> None:
        self._dir = feedback_dir(session_dir)
        # Hashes derived from frame images on disk, keyed by relative frame
        # path. `load()` rebuilds its response objects on every call, so the
        # derived value has to be cached here rather than on the response.
        # Failures are cached as `[]` too, so a missing or corrupt frame is not
        # reopened on every captured frame.
        self._derived_hashes: dict[str, list[str]] = {}

    def _stem(self, response: FeedbackResponse) -> str:
        return f"{response.timestamp.strftime('%Y%m%d_%H%M%S')}_{response.mode}"

    @property
    def _session_dir(self) -> Path:
        """The session directory `self._dir` lives under (see `paths.feedback_dir`)."""
        return self._dir.parent

    def _relative_frame_path(self, last_frame: CapturedFrame | None) -> str | None:
        """`last_frame`'s path relative to the session dir, for storing in JSON.

        Stored relative so a session directory stays valid if the data dir moves.
        Falls back to None for a frame outside this session (nothing to reference).
        """
        if last_frame is None or last_frame.path is None:
            return None
        try:
            return last_frame.path.relative_to(self._session_dir).as_posix()
        except ValueError:
            return None

    def save(
        self,
        response: FeedbackResponse,
        last_frame: CapturedFrame | None,
        overlay_image: PilImage.Image | None = None,
    ) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        stem = self._stem(response)
        # Record the frame reference on the live object too, so a just-generated
        # entry resolves its frame exactly like one reloaded from disk.
        response.frame_path = self._relative_frame_path(last_frame)

        data = {
            "mode": response.mode,
            "text": response.text,
            "timestamp": response.timestamp.isoformat(),
            "annotation_json": response.annotation_json,
            "observations": response.observations,
            "used_structured_output": response.used_structured_output,
            "frame_hashes": response.frame_hashes,
            "frame_path": response.frame_path,
        }
        (self._dir / f"{stem}.json").write_text(json.dumps(data, indent=2))

        if overlay_image is not None:
            overlay_image.save(self._dir / f"{stem}_overlay.png", format="PNG")

    def load(self) -> list[FeedbackResponse]:
        if not self._dir.is_dir():
            return []
        results: list[FeedbackResponse] = []
        for json_path in sorted(self._dir.glob("*.json")):
            try:
                data = json.loads(json_path.read_text())
                response = FeedbackResponse(
                    mode=data["mode"],
                    text=data["text"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    annotation_json=data.get("annotation_json"),
                    observations=data.get("observations", []),
                    used_structured_output=data.get("used_structured_output", False),
                    frame_hashes=data.get("frame_hashes", []),
                    frame_path=data.get("frame_path"),
                )
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                _log.warning("Skipping malformed feedback file %s: %s", json_path, exc)
                continue
            results.append(response)
        return results

    def overlay_image_for(self, response: FeedbackResponse) -> PilImage.Image | None:
        overlay_path = self._dir / f"{self._stem(response)}_overlay.png"
        if not overlay_path.is_file():
            return None
        return PilImage.open(overlay_path).convert("RGB")

    def frame_path_for(self, response: FeedbackResponse) -> Path | None:
        """The full-resolution frame `response` was based on, if still on disk.

        Returns None for entries saved before frame paths were recorded, and for
        frames since removed (e.g. by session pruning).
        """
        if not response.frame_path:
            return None
        frame_path = self._session_dir / response.frame_path
        return frame_path if frame_path.is_file() else None

    def _hashes_for(self, response: FeedbackResponse) -> list[str]:
        """`response`'s frame hashes, derived from its frame on disk if unrecorded.

        Returns `[]` when the hashes are unknown — not recorded and not
        recoverable — which callers must treat as "never matches" rather than as
        a fingerprint. Derivation is in-memory; the entry's JSON is not rewritten.
        """
        if response.frame_hashes:
            return response.frame_hashes
        if not response.frame_path:
            return []
        cached = self._derived_hashes.get(response.frame_path)
        if cached is not None:
            return cached

        derived: list[str] = []
        frame_path = self.frame_path_for(response)
        if frame_path is not None:
            try:
                # Decoded exactly as `CaptureEngine._load_frames_from_disk()`
                # does — no `.convert("RGB")`, unlike `overlay_image_for()`.
                # `tobytes()` is mode-dependent, so a derived hash only compares
                # equal to a live one if both sides decode the file the same way.
                image = PilImage.open(frame_path).copy()
                derived = [hashlib.sha256(image.tobytes()).hexdigest()]
            except Exception as exc:
                _log.warning("Cannot hash frame %s: %s", frame_path, exc)

        self._derived_hashes[response.frame_path] = derived
        return derived

    def last_entry_for(
        self, mode: str, frame_hashes: list[str]
    ) -> FeedbackResponse | None:
        # An empty hash list means "no fingerprint available" — for the caller,
        # no frames captured yet; for an entry, hashes neither recorded nor
        # recoverable from disk. It is never a value two sides can match on, so
        # both empty cases bail rather than comparing equal to each other.
        if not frame_hashes:
            return None
        for response in reversed(self.load()):
            if response.mode != mode:
                continue
            hashes = self._hashes_for(response)
            if hashes and hashes == frame_hashes:
                return response
        return None
