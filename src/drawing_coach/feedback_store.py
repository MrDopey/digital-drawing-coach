from __future__ import annotations

import json
from pathlib import Path

from PIL import Image as PilImage

from drawing_coach.capture_engine import CapturedFrame
from drawing_coach.feedback_engine import FeedbackResponse
from drawing_coach.paths import feedback_dir

_THUMBNAIL_SIZE = (160, 160)


class FeedbackStore:
    """Disk persistence for `FeedbackResponse` entries within one session."""

    def __init__(self, session_dir: Path) -> None:
        self._dir = feedback_dir(session_dir)

    def _stem(self, response: FeedbackResponse) -> str:
        return f"{response.timestamp.strftime('%Y%m%d_%H%M%S')}_{response.mode}"

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
        }
        (self._dir / f"{stem}.json").write_text(json.dumps(data, indent=2))

        if last_frame is not None:
            thumb = last_frame.image.copy()
            thumb.thumbnail(_THUMBNAIL_SIZE)
            thumb.convert("RGB").save(self._dir / thumb_name, format="JPEG")

        if overlay_image is not None:
            overlay_image.save(self._dir / f"{stem}_overlay.png", format="PNG")
