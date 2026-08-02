from __future__ import annotations

import base64
import hashlib
import io
import json
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

_CATEGORY_EXAMPLES = "anatomy, perspective, color_theory, composition, line_quality"

_PERSONA = """You are an expert digital art coach with deep knowledge of \
perspective, anatomy, color theory, composition, and digital painting technique. \
You give clear, specific, actionable feedback tailored to what you observe in the \
user's drawing. Be encouraging but honest.

You will be provided with one or more images captured during a drawing session. \
When multiple images are provided, they are ordered chronologically — the first image \
is the earliest capture and the last is the most recent. Image filenames contain \
timestamps so you can infer the time elapsed between captures. Use this progression \
to comment on how the work has evolved: note what has improved, what has stalled, \
and what the artist should focus on next."""

_OBSERVATIONS_COMMENT_INSTRUCTION = f"""After your visible feedback, append an HTML comment capturing structured observations \
for future reference, in this exact format: \
<!-- observations: [{{"category": "perspective", \
"note": "Struggles with vanishing points"}}] --> \
Use short lowercase categories (e.g. {_CATEGORY_EXAMPLES}) and concise notes. Include \
the comment even if the array is empty. Never mention this comment in your visible \
feedback."""

_SYSTEM_PROMPT = _PERSONA + "\n\n" + _OBSERVATIONS_COMMENT_INSTRUCTION

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

_MODE_TEMPLATES_STRUCTURED_OVERRIDES = {
    "overlay": (
        "Analyse this drawing and populate the `annotations` field with your "
        "corrections. Each annotation must be one of:\n"
        '  {"type":"arrow","from":[x1,y1],"to":[x2,y2],"label":"..."}\n'
        '  {"type":"line","points":[[x1,y1],[x2,y2]],"color":"red"}\n'
        '  {"type":"circle","center":[cx,cy],"radius":r,"label":"..."}\n'
        "All coordinates are normalised 0–1 relative to image width/height. Leave "
        "`annotations` as an empty array if there are none. Put your explanatory "
        "text in `feedback_text`."
    ),
}

_POLICY_PHRASES = ("i'm unable to", "i cannot assist", "content policy", "i can't help")
_RATE_LIMIT_SECONDS = 10

_STRUCTURED_UNAVAILABLE_MESSAGE = (
    "Structured JSON output isn't available this session — memory notes and "
    "overlay annotations will use a less-reliable text-parsing fallback until "
    "you restart the app."
)

_STRUCTURED_RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "coaching_feedback",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "feedback_text": {
                    "type": "string",
                    "description": "The visible coaching feedback shown to the user.",
                },
                "observations": {
                    "type": "array",
                    "description": (
                        "Structured observations for future reference. Use short "
                        f"lowercase categories (e.g. {_CATEGORY_EXAMPLES}) and "
                        "concise notes. Empty array if none."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "note": {"type": "string"},
                        },
                        "required": ["category", "note"],
                        "additionalProperties": False,
                    },
                },
                "annotations": {
                    "type": "array",
                    "description": (
                        "Only populated in overlay mode. Normalised coordinates "
                        "(0.0-1.0 relative to image width/height). Empty array "
                        "otherwise."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["arrow", "line", "circle"],
                            },
                            "from": {
                                "type": ["array", "null"],
                                "items": {"type": "number"},
                            },
                            "to": {
                                "type": ["array", "null"],
                                "items": {"type": "number"},
                            },
                            "points": {
                                "type": ["array", "null"],
                                "items": {
                                    "type": "array",
                                    "items": {"type": "number"},
                                },
                            },
                            "center": {
                                "type": ["array", "null"],
                                "items": {"type": "number"},
                            },
                            "radius": {"type": ["number", "null"]},
                            "color": {"type": ["string", "null"]},
                            "label": {"type": ["string", "null"]},
                        },
                        "required": [
                            "type",
                            "from",
                            "to",
                            "points",
                            "center",
                            "radius",
                            "color",
                            "label",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["feedback_text", "observations", "annotations"],
            "additionalProperties": False,
        },
    },
}

# Process-lifetime flag: once structured output fails once, every subsequent
# request in this run goes straight to the prose fallback (see design.md).
_structured_output_disabled = False


def _reset_structured_output_state() -> None:
    """Test-only: reset the process-lifetime structured-output-disabled flag."""
    global _structured_output_disabled
    _structured_output_disabled = False


@dataclass
class FeedbackResponse:
    mode: str
    text: str
    timestamp: datetime = field(default_factory=datetime.now)
    annotation_json: str | None = None  # raw JSON string for overlay mode
    observations: list[dict] = field(default_factory=list)
    used_structured_output: bool = False
    frame_hashes: list[str] = field(default_factory=list)


class FeedbackEngine:
    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._history: list[FeedbackResponse] = []
        self._last_call: float = 0.0
        self.on_feedback: Callable[[FeedbackResponse], None] | None = None
        self.on_structured_output_unavailable: Callable[[str], None] | None = None

    def get_history(self) -> list[FeedbackResponse]:
        return list(self._history)

    def request_feedback(
        self,
        frames: list[CapturedFrame],
        mode: str = "full_critique",
        coach_notes: str = "",
    ) -> FeedbackResponse | str:
        """Returns FeedbackResponse on success, or an error string."""
        global _structured_output_disabled

        if not self._config.is_configured():
            return "No LLM configured — open Settings to add your model details"

        if not frames:
            return "No drawing captured yet — please wait for the first screenshot"

        elapsed = time.monotonic() - self._last_call
        if elapsed < _RATE_LIMIT_SECONDS:
            remaining = int(_RATE_LIMIT_SECONDS - elapsed)
            _log.warning("Rate limit: %ds remaining before next request", remaining)
            return f"Please wait {remaining}s before requesting feedback again"

        self._last_call = time.monotonic()
        _log.info(
            "LLM request: model=%s mode=%s frames=%d",
            self._config.model,
            mode,
            len(frames),
        )

        selected_frames = self._select_frames(frames, mode)
        frame_hashes = [
            hashlib.sha256(frame.image.tobytes()).hexdigest()
            for frame in selected_frames
        ]

        try:
            if not _structured_output_disabled:
                try:
                    result = self._call_structured(
                        frames, mode, coach_notes, frame_hashes
                    )
                except (
                    litellm.exceptions.AuthenticationError,
                    litellm.exceptions.RateLimitError,
                    litellm.exceptions.NotFoundError,
                ):
                    raise
                except Exception as exc:
                    _log.debug(
                        "Structured output unavailable (%s) — disabling for this "
                        "session and falling back to prose parsing",
                        exc,
                    )
                    _structured_output_disabled = True
                    if self.on_structured_output_unavailable:
                        self.on_structured_output_unavailable(
                            _STRUCTURED_UNAVAILABLE_MESSAGE
                        )
                    result = self._call_prose(frames, mode, coach_notes, frame_hashes)
            else:
                result = self._call_prose(frames, mode, coach_notes, frame_hashes)

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

        if isinstance(result, FeedbackResponse):
            self._history.append(result)
            if self.on_feedback:
                self.on_feedback(result)
        return result

    # ------------------------------------------------------------------
    # Request paths
    # ------------------------------------------------------------------

    def _call_structured(
        self,
        frames: list[CapturedFrame],
        mode: str,
        coach_notes: str,
        frame_hashes: list[str],
    ) -> FeedbackResponse | str:
        system = self._build_system_prompt(mode, coach_notes, structured=True)
        messages = self._build_messages(system, frames, mode)

        kwargs = self._base_kwargs(f"feedback_{mode}_structured")
        kwargs["messages"] = messages
        kwargs["response_format"] = _STRUCTURED_RESPONSE_SCHEMA

        t0 = time.monotonic()
        response = litellm.completion(**kwargs)
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        raw_text = response.choices[0].message.content or ""

        if any(phrase in raw_text.lower() for phrase in _POLICY_PHRASES):
            _log.warning("LLM policy refusal detected (structured attempt)")
            return (
                "The LLM flagged a content policy issue with this image — "
                "try a different feedback mode or drawing"
            )

        parsed = json.loads(raw_text)
        _validate_structured_response(parsed, mode)
        _log.info("Structured LLM response received in %dms", elapsed_ms)

        annotation_json = None
        if mode == "overlay":
            annotation_json = json.dumps(
                {"annotations": parsed.get("annotations", [])}
            )

        return FeedbackResponse(
            mode=mode,
            text=parsed["feedback_text"],
            annotation_json=annotation_json,
            observations=parsed.get("observations", []),
            used_structured_output=True,
            frame_hashes=frame_hashes,
        )

    def _call_prose(
        self,
        frames: list[CapturedFrame],
        mode: str,
        coach_notes: str,
        frame_hashes: list[str],
    ) -> FeedbackResponse | str:
        system = self._build_system_prompt(mode, coach_notes, structured=False)
        messages = self._build_messages(system, frames, mode)

        kwargs = self._base_kwargs(f"feedback_{mode}_prose")
        kwargs["messages"] = messages

        t0 = time.monotonic()
        response = litellm.completion(**kwargs)
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        text = response.choices[0].message.content or ""

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

        return FeedbackResponse(
            mode=mode,
            text=text,
            annotation_json=annotation_json,
            frame_hashes=frame_hashes,
        )

    # ------------------------------------------------------------------

    def _base_kwargs(self, label: str) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self._config.model,
            "metadata": {"debug_label": label},
        }
        if self._config.api_key:
            kwargs["api_key"] = self._config.api_key
        if self._config.api_base:
            kwargs["api_base"] = self._config.api_base
        return kwargs

    def _build_system_prompt(
        self, mode: str, coach_notes: str = "", structured: bool = False
    ) -> str:
        parts = [_PERSONA if structured else _SYSTEM_PROMPT]
        style_fragment = self._config.style_prompt_fragment()
        if style_fragment:
            parts.append(style_fragment)
        if self._config.custom_instructions:
            parts.append(self._config.custom_instructions)
        if structured:
            mode_template = _MODE_TEMPLATES_STRUCTURED_OVERRIDES.get(
                mode, _MODE_TEMPLATES.get(mode, _MODE_TEMPLATES["full_critique"])
            )
        else:
            mode_template = _MODE_TEMPLATES.get(mode, _MODE_TEMPLATES["full_critique"])
        parts.append(mode_template)
        if coach_notes:
            parts.append(coach_notes)
        return "\n\n".join(parts)

    def _select_frames(
        self, frames: list[CapturedFrame], mode: str
    ) -> list[CapturedFrame]:
        if mode == "overlay":
            # Annotation coordinates are normalised relative to a single image;
            # sending lookback frames would leave the LLM's coordinates
            # ambiguous about which image they describe.
            return [frames[-1]]
        lookback = max(0, self._config.lookback_frames)
        # latest frame + up to `lookback` prior frames
        if lookback == 0:
            return [frames[-1]]
        return frames[-(lookback + 1) :]

    def _build_messages(
        self, system: str, frames: list[CapturedFrame], mode: str
    ) -> list[dict[str, object]]:
        selected = self._select_frames(frames, mode)

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


def _validate_structured_response(parsed: Any, mode: str) -> None:
    if not isinstance(parsed, dict):
        raise ValueError("structured response is not a JSON object")
    if not isinstance(parsed.get("feedback_text"), str) or not parsed["feedback_text"]:
        raise ValueError("structured response missing feedback_text")
    if not isinstance(parsed.get("observations"), list):
        raise ValueError("structured response missing observations array")
    if mode == "overlay" and not isinstance(parsed.get("annotations"), list):
        raise ValueError(
            "structured response missing annotations array for overlay mode"
        )


def _extract_json_block(text: str) -> str | None:
    import re

    m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    return m.group(1).strip() if m else None


def _strip_json_block(text: str) -> str:
    import re

    return re.sub(r"```json.*?```", "", text, flags=re.DOTALL).strip()
