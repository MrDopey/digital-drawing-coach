from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from PIL import Image as PilImage

from drawing_coach.capture_engine import CapturedFrame
from drawing_coach.feedback_engine import FeedbackResponse
from drawing_coach.paths import feedback_dir

_log = logging.getLogger("drawing_coach.feedback_store")

_THUMBNAIL_SIZE = (160, 160)


class FeedbackStore:
    """Disk persistence for `FeedbackResponse` entries within one session."""

    def __init__(self, session_dir: Path) -> None:
        self._dir = feedback_dir(session_dir)

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
        thumb_name = f"{stem}_thumb.jpg"

        data = {
            "mode": response.mode,
            "text": response.text,
            "timestamp": response.timestamp.isoformat(),
            "annotation_json": response.annotation_json,
            "observations": response.observations,
            "used_structured_output": response.used_structured_output,
            "frame_hashes": response.frame_hashes,
            "thumbnail_path": thumb_name,
            "frame_path": self._relative_frame_path(last_frame),
        }
        (self._dir / f"{stem}.json").write_text(json.dumps(data, indent=2))

        if last_frame is not None:
            thumb = last_frame.image.copy()
            thumb.thumbnail(_THUMBNAIL_SIZE)
            thumb.convert("RGB").save(self._dir / thumb_name, format="JPEG")

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

    def thumbnail_path_for(self, response: FeedbackResponse) -> Path | None:
        thumb_path = self._dir / f"{self._stem(response)}_thumb.jpg"
        return thumb_path if thumb_path.is_file() else None

    def frame_path_for(self, response: FeedbackResponse) -> Path | None:
        """The full-resolution frame `response` was based on, if still on disk.

        Returns None for entries saved before frame paths were recorded, and for
        frames since removed (e.g. by session pruning).
        """
        if not response.frame_path:
            return None
        frame_path = self._session_dir / response.frame_path
        return frame_path if frame_path.is_file() else None

    def last_entry_for(
        self, mode: str, frame_hashes: list[str]
    ) -> FeedbackResponse | None:
        for response in reversed(self.load()):
            if response.mode == mode and response.frame_hashes == frame_hashes:
                return response
        return None
