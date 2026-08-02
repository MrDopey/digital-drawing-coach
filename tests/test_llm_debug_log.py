"""Unit tests for DebugIOLogger, LiteLLM's CustomLogger callback used to
persist LLM request/response pairs to disk for offline debugging."""

import base64
import logging
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from drawing_coach.llm_config import LLMConfig
from drawing_coach.llm_debug_log import DebugIOLogger


def _b64_png() -> str:
    import io

    buf = io.BytesIO()
    Image.new("RGB", (4, 4)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _kwargs(label: str, n_images: int = 0) -> dict:
    content = [{"type": "text", "text": "Please review my drawing:"}]
    for _ in range(n_images):
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{_b64_png()}"},
            }
        )
    return {
        "messages": [
            {"role": "system", "content": "You are a coach."},
            {"role": "user", "content": content},
        ],
        "litellm_params": {"metadata": {"debug_label": label}},
    }


def _mock_response(text: str):
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def debug_dir(tmp_path):
    d = tmp_path / "debug_logs"
    with patch("drawing_coach.llm_debug_log.paths.debug_log_dir", return_value=d):
        yield d


def test_disabled_config_writes_no_files(debug_dir):
    logger = DebugIOLogger(LLMConfig(debug_log_llm_io=False))
    logger.log_success_event(_kwargs("feedback_overlay_structured", n_images=1), _mock_response("ok"), None, None)
    assert not debug_dir.exists()


def test_enabled_writes_frames_request_and_response_on_success(debug_dir):
    logger = DebugIOLogger(LLMConfig(debug_log_llm_io=True))
    logger.log_success_event(
        _kwargs("feedback_overlay_structured", n_images=2),
        _mock_response("Great composition!"),
        None,
        None,
    )

    subdirs = list(debug_dir.iterdir())
    assert len(subdirs) == 1
    out_dir = subdirs[0]
    assert out_dir.name.endswith("_feedback_overlay_structured")

    assert (out_dir / "frame_00.png").exists()
    assert (out_dir / "frame_01.png").exists()
    assert not (out_dir / "frame_02.png").exists()

    request_text = (out_dir / "request.txt").read_text()
    assert "SYSTEM: You are a coach." in request_text
    assert "USER: Please review my drawing:" in request_text

    assert (out_dir / "response.txt").read_text() == "Great composition!"
    assert not (out_dir / "error.txt").exists()


def test_enabled_writes_request_and_error_on_failure(debug_dir):
    logger = DebugIOLogger(LLMConfig(debug_log_llm_io=True))
    kwargs = _kwargs("diagnostics_check_llm")
    kwargs["exception"] = ValueError("bad key")

    logger.log_failure_event(kwargs, None, None, None)

    out_dir = next(debug_dir.iterdir())
    assert out_dir.name.endswith("_diagnostics_check_llm")
    assert (out_dir / "request.txt").exists()
    assert (out_dir / "error.txt").read_text() == "ValueError: bad key"
    assert not (out_dir / "response.txt").exists()


def test_write_failure_logs_warning_and_does_not_raise(tmp_path, caplog):
    # debug_log_dir() resolves under a path component that is actually a
    # regular file, so mkdir(parents=True) raises.
    blocked = tmp_path / "not_a_dir"
    blocked.write_text("")
    unwritable = blocked / "debug_logs"

    logger = DebugIOLogger(LLMConfig(debug_log_llm_io=True))
    with patch(
        "drawing_coach.llm_debug_log.paths.debug_log_dir", return_value=unwritable
    ):
        with caplog.at_level(logging.WARNING, logger="drawing_coach.llm_debug_log"):
            logger.log_success_event(
                _kwargs("feedback_quick_hint_prose"), _mock_response("ok"), None, None
            )

    assert any("Debug log write failed" in rec.message for rec in caplog.records)
