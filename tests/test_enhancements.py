"""Tests for drawing-coach-enhancements: dedup, error handling, overlay, style."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import numpy as np
from PIL import Image

from drawing_coach.capture_engine import CapturedFrame, _compute_mae
from drawing_coach.feedback_engine import FeedbackEngine
from drawing_coach.llm_config import LLMConfig
from drawing_coach.overlay_renderer import render as render_overlay

# ------------------------------------------------------------------
# 3.3  Dedup MAE helper
# ------------------------------------------------------------------


def _solid(v: int, size: int = 64) -> Image.Image:
    return Image.fromarray(np.full((size, size), v, dtype=np.uint8))


def test_mae_identical_images_is_zero():
    img = _solid(128)
    assert _compute_mae(img, img) < 0.01


def test_mae_different_images():
    assert _compute_mae(_solid(0), _solid(100)) > 90.0


def test_mae_boundary_at_threshold():
    a = _solid(50)
    b = _solid(52)
    mae = _compute_mae(a, b)
    assert 1.5 < mae < 3.0  # just above dedup default of 2.0


# ------------------------------------------------------------------
# 7.5  Error types
# ------------------------------------------------------------------


def _engine() -> FeedbackEngine:
    cfg = LLMConfig(model="gpt-4o")
    e = FeedbackEngine(cfg)
    e._last_call = 0
    return e


def _frame() -> CapturedFrame:
    return CapturedFrame(image=Image.new("RGB", (64, 64)))


def _mock_resp(text: str):
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_rate_limit_error():
    import litellm

    engine = _engine()
    with patch(
        "litellm.completion",
        side_effect=litellm.exceptions.RateLimitError(
            "rate limit", llm_provider="openai", model="gpt-4o"
        ),
    ):
        result = engine.request_feedback([_frame()])
    assert isinstance(result, str)
    assert "Rate limit" in result


def test_quota_error_via_message():
    engine = _engine()
    with patch("litellm.completion", side_effect=Exception("quota exceeded")):
        result = engine.request_feedback([_frame()])
    assert isinstance(result, str)
    assert "credits" in result.lower() or "quota" in result.lower()


def test_model_not_found_error():
    import litellm

    engine = _engine()
    with patch(
        "litellm.completion",
        side_effect=litellm.exceptions.NotFoundError(
            "not found", llm_provider="openai", model="gpt-4o"
        ),
    ):
        result = engine.request_feedback([_frame()])
    assert isinstance(result, str)
    assert "not found" in result.lower()


def test_policy_refusal_detected():
    engine = _engine()
    with patch(
        "litellm.completion",
        return_value=_mock_resp(
            "I'm unable to assist with this request due to content policy."
        ),
    ):
        result = engine.request_feedback([_frame()])
    assert isinstance(result, str)
    assert "content policy" in result.lower() or "policy" in result.lower()


# ------------------------------------------------------------------
# 8.10  Overlay renderer
# ------------------------------------------------------------------

_ANNOTATION_JSON = json.dumps(
    {
        "annotations": [
            {
                "type": "arrow",
                "from": [0.1, 0.1],
                "to": [0.5, 0.5],
                "label": "fix this",
            },
            {"type": "line", "points": [[0.0, 0.0], [1.0, 1.0]], "color": "blue"},
            {"type": "circle", "center": [0.5, 0.5], "radius": 0.1, "label": "here"},
        ]
    }
)


def test_overlay_renders_to_image():
    img = Image.new("RGB", (200, 200), (200, 200, 200))
    result, err = render_overlay(img, _ANNOTATION_JSON)
    assert err is None
    assert result.size == img.size


def test_overlay_fallback_on_bad_json():
    img = Image.new("RGB", (100, 100))
    result, err = render_overlay(img, "this is not json")
    assert err is not None
    assert "unavailable" in err.lower()
    assert result is img  # original returned unchanged


def test_overlay_fallback_on_missing_annotations_key():
    img = Image.new("RGB", (100, 100))
    result, err = render_overlay(img, '{"something_else": []}')
    assert err is None  # valid JSON, just empty annotations
    assert result.size == img.size


# ------------------------------------------------------------------
# 9.1  Style injection in system prompt
# ------------------------------------------------------------------


def test_style_preset_injected_in_prompt():
    cfg = LLMConfig(
        model="gpt-4o", style_focus="Anime/Manga", style_focus_is_preset=True
    )
    engine = FeedbackEngine(cfg)
    engine._last_call = 0

    captured = []

    def _capture(**kwargs):
        captured.extend(kwargs["messages"])
        return _mock_resp("ok")

    with patch("litellm.completion", side_effect=_capture):
        engine.request_feedback([_frame()])

    system = captured[0]["content"]
    assert "Anime/Manga" in system
    assert "practising" in system


def test_freetext_focus_injected_in_prompt():
    cfg = LLMConfig(
        model="gpt-4o", style_focus="gothic pokemon", style_focus_is_preset=False
    )
    engine = FeedbackEngine(cfg)
    engine._last_call = 0

    captured = []

    def _capture(**kwargs):
        captured.extend(kwargs["messages"])
        return _mock_resp("ok")

    with patch("litellm.completion", side_effect=_capture):
        engine.request_feedback([_frame()])

    system = captured[0]["content"]
    assert "gothic pokemon" in system
    assert "focusing on" in system


def test_no_style_no_injection():
    cfg = LLMConfig(model="gpt-4o", style_focus="")
    engine = FeedbackEngine(cfg)
    engine._last_call = 0

    captured = []

    def _capture(**kwargs):
        captured.extend(kwargs["messages"])
        return _mock_resp("ok")

    with patch("litellm.completion", side_effect=_capture):
        engine.request_feedback([_frame()])

    system = captured[0]["content"]
    assert "practising" not in system
    assert "focusing on" not in system


# ------------------------------------------------------------------
# 9.5  Rate-limit error message (also covered in 7.5)
# ------------------------------------------------------------------


def test_rate_limit_shows_correct_message():
    import litellm

    engine = _engine()
    with patch(
        "litellm.completion",
        side_effect=litellm.exceptions.RateLimitError(
            "too many requests", llm_provider="openai", model="gpt-4o"
        ),
    ):
        result = engine.request_feedback([_frame()])
    assert "wait" in result.lower() or "rate limit" in result.lower()
