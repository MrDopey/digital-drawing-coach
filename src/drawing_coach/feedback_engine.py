from __future__ import annotations

import base64
import io
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

import litellm
from PIL import Image

from drawing_coach.capture_engine import CapturedFrame
from drawing_coach.llm_config import LLMConfig

_log = logging.getLogger("drawing_coach.feedback_engine")

_SYSTEM_PROMPT = """You are an expert digital art coach with deep knowledge of \
perspective, anatomy, color theory, composition, and digital painting technique. \
You give clear, specific, actionable feedback tailored to what you observe in the \
user's drawing. Be encouraging but honest.

You will be provided with one or more images captured during a drawing session. \
When multiple images are provided, they are ordered chronologically — the first image \
is the earliest capture and the last is the most recent. Image filenames contain \
timestamps so you can infer the time elapsed between captures. Use this progression \
to comment on how the work has evolved: note what has improved, what has stalled, \
and what the artist should focus on next.

After your visible feedback, append an HTML comment capturing structured observations \
for future reference, in this exact format: \
<!-- observations: [{"category": "perspective", \
"note": "Struggles with vanishing points"}] --> \
Use short lowercase categories (e.g. anatomy, perspective, color_theory, composition, \
line_quality) and concise notes. Include the comment even if the array is empty. Never \
mention this comment in your visible feedback."""

_MODE_TEMPLATES = {
    "quick_hint": (
        "In ONE sentence (maximum 30 words), identify the single most pressing issue "
        "you see in this drawing."
    ),
    "full_critique": (
        "Provide a structured critique with the following sections:\n"
        "## Composition\n## Technique\n## Anatomy / Perspective\n## Next Steps\n"
        "Be specific and reference what you observe."
    ),
    "practice_exercise": (
        "Based on the main weakness you observe, describe ONE specific practice"
        " exercise the artist should do next to improve that area."
        " Be concrete and actionable."
    ),
    "overlay": (
        "Analyse this drawing and return your response in two parts:\n\n"
        "1. A short explanation of the corrections (plain text).\n\n"
        "2. A JSON block (delimited by ```json and ```) with an `annotations` array. "
        "Each annotation must be one of:\n"
        '  {"type":"arrow","from":[x1,y1],"to":[x2,y2],"label":"..."}\n'
        '  {"type":"line","points":[[x1,y1],[x2,y2]],"color":"red"}\n'
        '  {"type":"circle","center":[cx,cy],"radius":r,"label":"..."}\n'
        "All coordinates are normalised 0–1 relative to image width/height.\n"
        "Return the JSON block even if there are no annotations (use an empty array)."
    ),
}

_POLICY_PHRASES = ("i'm unable to", "i cannot assist", "content policy", "i can't help")
_RATE_LIMIT_SECONDS = 10


@dataclass
class FeedbackResponse:
    mode: str
    text: str
    timestamp: datetime = field(default_factory=datetime.now)
    annotation_json: str | None = None  # raw JSON string for overlay mode


class FeedbackEngine:
    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._history: list[FeedbackResponse] = []
        self._last_call: float = 0.0
        self.on_feedback: Callable[[FeedbackResponse], None] | None = None

    def get_history(self) -> list[FeedbackResponse]:
        return list(self._history)

    def request_feedback(
        self,
        frames: list[CapturedFrame],
        mode: str = "full_critique",
        coach_notes: str = "",
    ) -> FeedbackResponse | str:
        """Returns FeedbackResponse on success, or an error string."""
        if not self._config.is_configured():
            return "No LLM configured — open Settings to add your model details"

        if not frames:
            return "No drawing captured yet — please wait for the first screenshot"

        elapsed = time.monotonic() - self._last_call
        if elapsed < _RATE_LIMIT_SECONDS:
            remaining = int(_RATE_LIMIT_SECONDS - elapsed)
            _log.warning("Rate limit: %ds remaining before next request", remaining)
            return f"Please wait {remaining}s before requesting feedback again"

        system = self._build_system_prompt(mode, coach_notes)
        messages = self._build_messages(system, frames, mode)

        kwargs: dict[str, Any] = {"model": self._config.model, "messages": messages}
        if self._config.api_key:
            kwargs["api_key"] = self._config.api_key
        if self._config.api_base:
            kwargs["api_base"] = self._config.api_base

        _log.info(
            "LLM request: model=%s mode=%s frames=%d",
            self._config.model,
            mode,
            len(frames),
        )
        try:
            t0 = time.monotonic()
            self._last_call = t0
            response = litellm.completion(**kwargs)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            text = response.choices[0].message.content or ""

            # Policy / copyright refusal detection
            if any(phrase in text.lower() for phrase in _POLICY_PHRASES):
                _log.warning("LLM policy refusal detected")
                return (
                    "The LLM flagged a content policy issue with this image — "
                    "try a different feedback mode or drawing"
                )

            _log.info("LLM response received in %dms", elapsed_ms)

            annotation_json: str | None = None
            if mode == "overlay":
                annotation_json = _extract_json_block(text)
                text = _strip_json_block(text)

            result = FeedbackResponse(
                mode=mode, text=text, annotation_json=annotation_json
            )
            self._history.append(result)
            if self.on_feedback:
                self.on_feedback(result)
            return result

        except litellm.exceptions.AuthenticationError:
            _log.error("LLM call failed: authentication error")
            return "API key invalid or missing — check your LLM settings"
        except litellm.exceptions.RateLimitError:
            _log.error("LLM call failed: rate limit exceeded")
            return "Rate limit reached — wait a moment and try again"
        except litellm.exceptions.NotFoundError:
            _log.error("LLM call failed: model not found (%s)", self._config.model)
            return "Model not found — check the model name in your LLM settings"
        except Exception as exc:
            _log.error("LLM call failed: %s", exc)
            msg = str(exc).lower()
            if "quota" in msg or "budget" in msg or "insufficient" in msg:
                return (
                    "Your API credits are exhausted — top up your account to continue"
                )
            if "network" in msg or "connection" in msg or "timeout" in msg:
                return "Network error — check your connection and try again"
            return f"LLM error: {exc}"

    # ------------------------------------------------------------------

    def _build_system_prompt(self, mode: str, coach_notes: str = "") -> str:
        parts = [_SYSTEM_PROMPT]
        style_fragment = self._config.style_prompt_fragment()
        if style_fragment:
            parts.append(style_fragment)
        if self._config.custom_instructions:
            parts.append(self._config.custom_instructions)
        parts.append(_MODE_TEMPLATES.get(mode, _MODE_TEMPLATES["full_critique"]))
        if coach_notes:
            parts.append(coach_notes)
        return "\n\n".join(parts)

    def _build_messages(
        self, system: str, frames: list[CapturedFrame], mode: str
    ) -> list[dict[str, object]]:
        if mode == "overlay":
            # Annotation coordinates are normalised relative to a single image;
            # sending lookback frames would leave the LLM's coordinates
            # ambiguous about which image they describe.
            selected = [frames[-1]]
        else:
            lookback = max(0, self._config.lookback_frames)
            # latest frame + up to `lookback` prior frames
            if lookback == 0:
                selected = [frames[-1]]
            else:
                selected = frames[-(lookback + 1) :]

        content: list[dict[str, object]] = [
            {"type": "text", "text": "Please review my drawing:"}
        ]
        for frame in selected:
            filename = (
                frame.path.name
                if frame.path
                else frame.timestamp.strftime("%Y%m%d_%H%M%S.png")
            )
            content.append({"type": "text", "text": f"[{filename}]"})
            b64 = _image_to_b64(frame.image)
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                }
            )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _image_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _extract_json_block(text: str) -> str | None:
    import re

    m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    return m.group(1).strip() if m else None


def _strip_json_block(text: str) -> str:
    import re

    return re.sub(r"```json.*?```", "", text, flags=re.DOTALL).strip()
