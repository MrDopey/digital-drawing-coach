"""Integration test for FeedbackEngine using a mocked LiteLLM response."""

import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from drawing_coach import feedback_engine as fe_module
from drawing_coach.capture_engine import CapturedFrame
from drawing_coach.feedback_engine import FeedbackEngine, FeedbackResponse
from drawing_coach.llm_config import LLMConfig
from drawing_coach.overlay_renderer import render as render_overlay


@pytest.fixture(autouse=True)
def _reset_structured_output_flag():
    """The structured-output-disabled flag is process-lifetime (module-level) by
    design, so each test must start and end with it unset for isolation."""
    fe_module._reset_structured_output_state()
    yield
    fe_module._reset_structured_output_state()


def _frame() -> CapturedFrame:
    return CapturedFrame(image=Image.new("RGB", (100, 100)))


def _configured_engine() -> FeedbackEngine:
    cfg = LLMConfig(model="gpt-4o")
    return FeedbackEngine(cfg)


def _mock_response(text: str):
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _mock_structured_response(feedback_text: str, observations=None, annotations=None):
    payload = {
        "feedback_text": feedback_text,
        "observations": observations or [],
        "annotations": annotations or [],
    }
    return _mock_response(json.dumps(payload))


def test_returns_error_when_no_config():
    cfg = LLMConfig()  # no model
    engine = FeedbackEngine(cfg)
    result = engine.request_feedback([_frame()])
    assert isinstance(result, str)
    assert "No LLM configured" in result


def test_returns_error_when_no_frames():
    engine = _configured_engine()
    result = engine.request_feedback([])
    assert isinstance(result, str)
    assert "No drawing" in result


def test_successful_feedback():
    engine = _configured_engine()
    engine._last_call = 0  # bypass rate limit

    with patch(
        "litellm.completion",
        return_value=_mock_response("Great work! Fix the arm rotation."),
    ):
        result = engine.request_feedback([_frame()], mode="quick_hint")

    assert isinstance(result, FeedbackResponse)
    assert result.mode == "quick_hint"
    assert "arm" in result.text


def test_auth_error_surface():
    import litellm

    engine = _configured_engine()
    engine._last_call = 0

    with patch(
        "litellm.completion",
        side_effect=litellm.exceptions.AuthenticationError(
            "bad key", llm_provider="openai", model="gpt-4o"
        ),
    ):
        result = engine.request_feedback([_frame()])

    assert isinstance(result, str)
    assert "API key" in result


def test_rate_limiting():
    engine = _configured_engine()
    engine._last_call = 0

    with patch("litellm.completion", return_value=_mock_response("ok")):
        engine.request_feedback([_frame()])

    result = engine.request_feedback([_frame()])
    assert isinstance(result, str)
    assert "wait" in result.lower()


def test_custom_instructions_in_prompt():
    cfg = LLMConfig(model="gpt-4o", custom_instructions="Focus on line confidence.")
    engine = FeedbackEngine(cfg)
    engine._last_call = 0

    captured_messages = []

    def _capture(**kwargs):
        captured_messages.extend(kwargs["messages"])
        return _mock_response("ok")

    with patch("litellm.completion", side_effect=_capture):
        engine.request_feedback([_frame()])

    system_content = captured_messages[0]["content"]
    assert "Focus on line confidence" in system_content


def test_coach_notes_appended_after_mode_template():
    engine = _configured_engine()
    prompt_without = engine._build_system_prompt("quick_hint")
    prompt_with = engine._build_system_prompt(
        "quick_hint", "You have worked with this student across 5 sessions."
    )

    assert prompt_with.startswith(prompt_without)
    assert prompt_with[len(prompt_without) :].strip() == (
        "You have worked with this student across 5 sessions."
    )


def test_coach_notes_omitted_when_empty():
    engine = _configured_engine()
    assert engine._build_system_prompt("quick_hint", "") == engine._build_system_prompt(
        "quick_hint"
    )


def test_coach_notes_variation_does_not_change_prefix():
    engine = _configured_engine()
    base = engine._build_system_prompt("full_critique")
    variant_a = engine._build_system_prompt("full_critique", "Notes version A.")
    variant_b = engine._build_system_prompt(
        "full_critique", "A much longer notes block, version B, with extra detail."
    )

    assert variant_a.startswith(base)
    assert variant_b.startswith(base)


def test_coach_notes_sent_to_llm_in_request():
    cfg = LLMConfig(model="gpt-4o")
    engine = FeedbackEngine(cfg)
    engine._last_call = 0

    captured_messages = []

    def _capture(**kwargs):
        captured_messages.extend(kwargs["messages"])
        return _mock_response("ok")

    with patch("litellm.completion", side_effect=_capture):
        engine.request_feedback([_frame()], coach_notes="Recurring theme: perspective.")

    system_content = captured_messages[0]["content"]
    assert "Recurring theme: perspective." in system_content


def test_history_accumulates():
    engine = _configured_engine()
    engine._last_call = 0

    with patch("litellm.completion", return_value=_mock_response("feedback 1")):
        engine.request_feedback([_frame()])

    engine._last_call = 0
    with patch("litellm.completion", return_value=_mock_response("feedback 2")):
        engine.request_feedback([_frame()])

    history = engine.get_history()
    assert len(history) == 2
    assert history[0].text == "feedback 1"
    assert history[1].text == "feedback 2"


def test_structured_output_success():
    engine = _configured_engine()
    engine._last_call = 0

    captured_kwargs = []

    def _capture(**kwargs):
        captured_kwargs.append(kwargs)
        return _mock_structured_response(
            "Great work!", observations=[{"category": "anatomy", "note": "arm ok"}]
        )

    with patch("litellm.completion", side_effect=_capture):
        result = engine.request_feedback([_frame()], mode="quick_hint")

    assert isinstance(result, FeedbackResponse)
    assert result.used_structured_output is True
    assert result.text == "Great work!"
    assert result.observations == [{"category": "anatomy", "note": "arm ok"}]
    assert len(captured_kwargs) == 1
    assert "response_format" in captured_kwargs[0]
    assert fe_module._structured_output_disabled is False


def test_structured_output_unsupported_falls_back_to_prose():
    engine = _configured_engine()
    engine._last_call = 0

    warnings = []
    engine.on_structured_output_unavailable = warnings.append

    call_count = {"n": 0}

    def _side_effect(**kwargs):
        call_count["n"] += 1
        if "response_format" in kwargs:
            raise TypeError("unexpected keyword argument 'response_format'")
        return _mock_response("Prose feedback text.")

    with patch("litellm.completion", side_effect=_side_effect):
        result = engine.request_feedback([_frame()], mode="quick_hint")

    assert isinstance(result, FeedbackResponse)
    assert result.used_structured_output is False
    assert result.text == "Prose feedback text."
    assert call_count["n"] == 2
    assert fe_module._structured_output_disabled is True
    assert warnings == [fe_module._STRUCTURED_UNAVAILABLE_MESSAGE]


def test_structured_output_invalid_json_falls_back(caplog):
    engine = _configured_engine()
    engine._last_call = 0

    call_count = {"n": 0}

    def _side_effect(**kwargs):
        call_count["n"] += 1
        if "response_format" in kwargs:
            return _mock_response("not valid json")
        return _mock_response("Prose feedback text.")

    with caplog.at_level(logging.DEBUG, logger="drawing_coach.feedback_engine"):
        with patch("litellm.completion", side_effect=_side_effect):
            result = engine.request_feedback([_frame()], mode="quick_hint")

    assert isinstance(result, FeedbackResponse)
    assert result.used_structured_output is False
    assert call_count["n"] == 2
    assert fe_module._structured_output_disabled is True
    assert any(
        "Structured output unavailable" in rec.message for rec in caplog.records
    )


def test_structured_output_skipped_when_already_disabled():
    fe_module._structured_output_disabled = True
    engine = _configured_engine()
    engine._last_call = 0

    warnings = []
    engine.on_structured_output_unavailable = warnings.append

    calls = []

    def _side_effect(**kwargs):
        calls.append(kwargs)
        return _mock_response("Prose feedback text.")

    with patch("litellm.completion", side_effect=_side_effect):
        engine.request_feedback([_frame()], mode="quick_hint")
        engine._last_call = 0
        engine.request_feedback([_frame()], mode="quick_hint")

    assert len(calls) == 2
    assert all("response_format" not in kwargs for kwargs in calls)
    assert warnings == []


def test_structured_output_overlay_annotations_from_schema():
    engine = _configured_engine()
    engine._last_call = 0

    annotations = [{"type": "circle", "center": [0.5, 0.5], "radius": 0.1}]
    with patch(
        "litellm.completion",
        return_value=_mock_structured_response(
            "Fix the head angle.", annotations=annotations
        ),
    ):
        result = engine.request_feedback([_frame()], mode="overlay")

    assert isinstance(result, FeedbackResponse)
    assert result.used_structured_output is True
    assert json.loads(result.annotation_json)["annotations"] == annotations


def test_overlay_structured_and_prose_fallback_render_identically():
    annotations = [{"type": "circle", "center": [0.5, 0.5], "radius": 0.1}]

    engine_structured = _configured_engine()
    engine_structured._last_call = 0
    with patch(
        "litellm.completion",
        return_value=_mock_structured_response(
            "Fix the head angle.", annotations=annotations
        ),
    ):
        structured_result = engine_structured.request_feedback(
            [_frame()], mode="overlay"
        )

    fe_module._structured_output_disabled = True
    engine_prose = _configured_engine()
    engine_prose._last_call = 0
    prose_text = (
        "Fix the head angle.\n\n"
        "```json\n"
        f'{{"annotations": {json.dumps(annotations)}}}\n'
        "```"
    )
    with patch("litellm.completion", return_value=_mock_response(prose_text)):
        prose_result = engine_prose.request_feedback([_frame()], mode="overlay")

    assert isinstance(structured_result, FeedbackResponse)
    assert isinstance(prose_result, FeedbackResponse)
    assert structured_result.used_structured_output is True
    assert prose_result.used_structured_output is False

    img = Image.new("RGB", (100, 100))
    structured_rendered, structured_err = render_overlay(
        img, structured_result.annotation_json
    )
    prose_rendered, prose_err = render_overlay(img, prose_result.annotation_json)

    assert structured_err is None
    assert prose_err is None
    assert structured_rendered.tobytes() == prose_rendered.tobytes()
