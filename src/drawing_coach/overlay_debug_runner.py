"""Shared LLM-calling logic for the overlay debug web tool and CLI."""

from __future__ import annotations

import base64
import io
import json

import litellm
from PIL import Image

from drawing_coach import paths
from drawing_coach.feedback_engine import (
    _MODE_TEMPLATES_STRUCTURED_OVERRIDES,
    _PERSONA,
    _STRUCTURED_RESPONSE_SCHEMA,
    _validate_structured_response,
)
from drawing_coach.llm_config import LLMConfig
from drawing_coach.overlay_debug_lib import compute_hypotheses, detect_canvas_bbox

DEFAULT_SYSTEM_PROMPT = (
    _PERSONA + "\n\n" + _MODE_TEMPLATES_STRUCTURED_OVERRIDES["overlay"]
)
DEFAULT_SCHEMA = _STRUCTURED_RESPONSE_SCHEMA


def run_debug_request(
    config: LLMConfig,
    image: Image.Image,
    system_prompt: str | None = None,
    response_format: dict | None = None,
    character_bbox: tuple[int, int, int, int] | None = None,
) -> dict:
    """Sends one overlay-mode request to the LLM and re-projects whatever
    annotations come back under every coordinate hypothesis. Always returns a
    dict with an "ok" bool; "warning" is set (without ok=False) when the LLM
    answered but the response didn't parse as valid structured output."""
    if not config.is_configured():
        return {"ok": False, "error": "No LLM configured — set one in Settings first"}

    system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
    response_format = response_format or DEFAULT_SCHEMA

    buf = io.BytesIO()
    image.save(buf, format="PNG")
    image_b64 = base64.b64encode(buf.getvalue()).decode()

    kwargs: dict = {
        "model": config.model,
        "response_format": response_format,
        "metadata": {"debug_label": "overlay_debug_tool"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please review my drawing:"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                ],
            },
        ],
    }
    if config.api_key:
        kwargs["api_key"] = config.api_key
    if config.api_base:
        kwargs["api_base"] = config.api_base

    try:
        response = litellm.completion(**kwargs)
    except Exception as exc:
        return {"ok": False, "error": f"LLM call failed: {exc}"}

    raw_text = response.choices[0].message.content or ""

    feedback_text = ""
    annotations: list[dict] = []
    warning = None
    try:
        parsed = json.loads(raw_text)
        _validate_structured_response(parsed, "overlay")
        feedback_text = parsed.get("feedback_text", "")
        annotations = parsed.get("annotations", [])
    except Exception as exc:
        warning = f"Could not parse a structured response: {exc}"

    canvas_bbox = detect_canvas_bbox(image)
    hypotheses = compute_hypotheses(
        annotations, image.width, image.height, canvas_bbox, character_bbox
    )

    return {
        "ok": True,
        "warning": warning,
        "image_w": image.width,
        "image_h": image.height,
        "canvas_bbox": canvas_bbox,
        "character_bbox": character_bbox,
        "feedback_text": feedback_text,
        "raw_response": raw_text,
        "model": config.model,
        "hypotheses": hypotheses,
        "debug_dump_dir": str(paths.debug_log_dir()),
    }
