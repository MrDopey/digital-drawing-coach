import json
from types import SimpleNamespace

import litellm
import pytest
from PIL import Image

from drawing_coach.llm_config import LLMConfig
from drawing_coach.overlay_debug_runner import run_debug_request


def _blank_image() -> Image.Image:
    return Image.new("RGB", (400, 300), color=(255, 255, 255))


def _fake_response(content: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


@pytest.fixture
def configured() -> LLMConfig:
    return LLMConfig(model="fake/test-model", api_key="fake-key")


def test_returns_error_without_configured_model():
    result = run_debug_request(LLMConfig(), _blank_image())
    assert result["ok"] is False
    assert "configured" in result["error"]


def test_successful_structured_response(monkeypatch, configured):
    payload = json.dumps(
        {
            "feedback_text": "looks good",
            "observations": [],
            "annotations": [
                {
                    "type": "circle",
                    "from": None,
                    "to": None,
                    "points": None,
                    "center": [0.5, 0.3],
                    "radius": 0.1,
                    "color": "red",
                    "label": "head",
                }
            ],
        }
    )
    monkeypatch.setattr(litellm, "completion", lambda **kw: _fake_response(payload))

    result = run_debug_request(configured, _blank_image())

    assert result["ok"] is True
    assert result["warning"] is None
    assert result["feedback_text"] == "looks good"
    assert result["raw_response"] == payload
    h0 = next(h for h in result["hypotheses"] if h["key"] == "h0")
    assert len(h0["shapes"]) == 1


def test_malformed_response_sets_warning_but_still_ok(monkeypatch, configured):
    monkeypatch.setattr(litellm, "completion", lambda **kw: _fake_response("not json"))

    result = run_debug_request(configured, _blank_image())

    assert result["ok"] is True
    assert "Could not parse" in result["warning"]
    assert result["raw_response"] == "not json"
    assert result["feedback_text"] == ""
    assert all(h["shapes"] == [] for h in result["hypotheses"])


def test_llm_call_failure_is_reported_as_not_ok(monkeypatch, configured):
    def boom(**kw):
        raise RuntimeError("network exploded")

    monkeypatch.setattr(litellm, "completion", boom)

    result = run_debug_request(configured, _blank_image())

    assert result["ok"] is False
    assert "network exploded" in result["error"]


def test_custom_prompt_and_schema_are_forwarded(monkeypatch, configured):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _fake_response(json.dumps({"feedback_text": "ok", "annotations": []}))

    monkeypatch.setattr(litellm, "completion", fake_completion)

    custom_schema = {"type": "json_schema", "json_schema": {"name": "custom"}}
    run_debug_request(
        configured,
        _blank_image(),
        system_prompt="a custom prompt",
        response_format=custom_schema,
    )

    assert captured["messages"][0] == {"role": "system", "content": "a custom prompt"}
    assert captured["response_format"] == custom_schema


def test_character_bbox_produces_h5(monkeypatch, configured):
    monkeypatch.setattr(
        litellm,
        "completion",
        lambda **kw: _fake_response(
            json.dumps({"feedback_text": "ok", "annotations": []})
        ),
    )

    result = run_debug_request(
        configured, _blank_image(), character_bbox=(10, 10, 100, 100)
    )

    assert any(h["key"] == "h5" for h in result["hypotheses"])
    assert result["character_bbox"] == (10, 10, 100, 100)
