"""Unit tests for LLMConfig validation and export/import."""

import json
from unittest.mock import call, patch

import pytest

from drawing_coach.llm_config import LLMConfig


def test_is_configured_false_when_empty():
    cfg = LLMConfig()
    assert not cfg.is_configured()


def test_is_configured_true_when_model_set():
    cfg = LLMConfig(model="gpt-4o")
    assert cfg.is_configured()


def test_save_and_load_round_trip(tmp_path):
    p = tmp_path / "config.json"
    with patch("drawing_coach.llm_config.config_path", return_value=p):
        cfg = LLMConfig(
            model="gpt-4o", api_base="http://localhost", capture_interval=60
        )
        cfg.save()
        loaded = LLMConfig.load()
    assert loaded.model == "gpt-4o"
    assert loaded.api_base == "http://localhost"
    assert loaded.capture_interval == 60


def test_load_returns_defaults_when_no_file(tmp_path):
    missing = tmp_path / "nope.json"
    with patch("drawing_coach.llm_config.config_path", return_value=missing):
        cfg = LLMConfig.load()
    assert cfg.model == ""
    assert cfg.capture_interval == 30


def test_export_excludes_api_key(tmp_path):
    cfg = LLMConfig(model="gpt-4o", api_base="http://x")
    out = tmp_path / "export.json"
    cfg.export_portable(out)
    data = json.loads(out.read_text())
    assert "api_key" not in data
    assert data["model"] == "gpt-4o"


def test_import_portable_sets_model_and_base(tmp_path):
    src = LLMConfig(model="claude-3-5-sonnet-20241022", api_base="http://proxy")
    out = tmp_path / "export.json"
    src.export_portable(out)
    imported = LLMConfig.import_portable(out)
    assert imported.model == "claude-3-5-sonnet-20241022"
    assert imported.api_base == "http://proxy"


def test_load_ignores_unknown_fields(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"model": "gpt-4o", "unknown_future_field": 42}))
    with patch("drawing_coach.llm_config.config_path", return_value=p):
        cfg = LLMConfig.load()
    assert cfg.model == "gpt-4o"


# --- api_key property ---

def test_api_key_getter_returns_env_var():
    with patch("drawing_coach.env.api_key", return_value="sk-from-env"):
        cfg = LLMConfig()
        assert cfg.api_key == "sk-from-env"


def test_api_key_getter_returns_empty_when_unset():
    with patch("drawing_coach.env.api_key", return_value=""):
        cfg = LLMConfig()
        assert cfg.api_key == ""


def test_api_key_setter_writes_to_dotenv(tmp_path):
    config_file = tmp_path / "config.json"
    with patch("drawing_coach.llm_config.config_path", return_value=config_file):
        with patch("drawing_coach.llm_config.set_key") as mock_set_key:
            cfg = LLMConfig()
            cfg.api_key = "sk-test"
            mock_set_key.assert_called_once_with(
                str(tmp_path / ".env"), "DRAWING_COACH_API_KEY", "sk-test"
            )


def test_api_key_setter_clears_via_unset_key(tmp_path):
    config_file = tmp_path / "config.json"
    with patch("drawing_coach.llm_config.config_path", return_value=config_file):
        with patch("drawing_coach.llm_config.unset_key") as mock_unset_key:
            cfg = LLMConfig()
            cfg.api_key = ""
            mock_unset_key.assert_called_once_with(
                str(tmp_path / ".env"), "DRAWING_COACH_API_KEY"
            )


def test_api_key_setter_raises_on_permission_error(tmp_path):
    config_file = tmp_path / "config.json"
    with patch("drawing_coach.llm_config.config_path", return_value=config_file):
        with patch(
            "drawing_coach.llm_config.set_key", side_effect=PermissionError("read-only")
        ):
            cfg = LLMConfig()
            with pytest.raises(PermissionError, match="Could not save API key"):
                cfg.api_key = "sk-test"
