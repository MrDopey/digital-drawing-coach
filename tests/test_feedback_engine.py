"""Integration test for FeedbackEngine using a mocked LiteLLM response."""

from unittest.mock import MagicMock, patch

from PIL import Image

from drawing_coach.capture_engine import CapturedFrame
from drawing_coach.feedback_engine import FeedbackEngine, FeedbackResponse
from drawing_coach.llm_config import LLMConfig


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
