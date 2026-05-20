"""Integration test for FeedbackEngine using a mocked LiteLLM response."""

from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
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
    cfg = LLMConfig()   # no model
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

    with patch("litellm.completion", return_value=_mock_response("Great work! Fix the arm rotation.")):
        result = engine.request_feedback([_frame()], mode="quick_hint")

    assert isinstance(result, FeedbackResponse)
    assert result.mode == "quick_hint"
    assert "arm" in result.text


def test_auth_error_surface():
    import litellm
    engine = _configured_engine()
    engine._last_call = 0

    with patch("litellm.completion", side_effect=litellm.exceptions.AuthenticationError("bad key", llm_provider="openai", model="gpt-4o")):
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
