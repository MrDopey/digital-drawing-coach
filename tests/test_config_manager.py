"""Unit tests for ConfigManager — precedence, persistence routing, and isolation."""

import json
import os
from unittest.mock import patch

import pytest

from drawing_coach.config_manager import ConfigManager
from drawing_coach.llm_config import LLMConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_manager(tmp_path):
    cp = tmp_path / "config.json"
    dp = tmp_path / ".env"
    return ConfigManager(config_path=cp, dotenv_path=dp)


# ---------------------------------------------------------------------------
# Guard: access before load
# ---------------------------------------------------------------------------

def test_config_raises_before_load(tmp_path):
    mgr = make_manager(tmp_path)
    with pytest.raises(RuntimeError, match="load()"):
        _ = mgr.config


# ---------------------------------------------------------------------------
# load() — missing files tolerated
# ---------------------------------------------------------------------------

def test_load_missing_config_uses_defaults(tmp_path):
    mgr = make_manager(tmp_path)
    cfg = mgr.load()
    assert cfg.model == ""
    assert cfg.capture_interval == 30


def test_load_missing_dotenv_tolerated(tmp_path):
    cp = tmp_path / "config.json"
    cp.write_text(json.dumps({"model": "gpt-4o"}))
    mgr = ConfigManager(config_path=cp, dotenv_path=tmp_path / ".env")
    cfg = mgr.load()
    assert cfg.model == "gpt-4o"


def test_load_reads_config_json(tmp_path):
    cp = tmp_path / "config.json"
    cp.write_text(json.dumps({"model": "claude-opus-4-8", "capture_interval": 60}))
    mgr = ConfigManager(config_path=cp, dotenv_path=tmp_path / ".env")
    cfg = mgr.load()
    assert cfg.model == "claude-opus-4-8"
    assert cfg.capture_interval == 60


def test_load_ignores_unknown_fields(tmp_path):
    cp = tmp_path / "config.json"
    cp.write_text(json.dumps({"model": "gpt-4o", "future_field": 99}))
    mgr = ConfigManager(config_path=cp, dotenv_path=tmp_path / ".env")
    cfg = mgr.load()
    assert cfg.model == "gpt-4o"


# ---------------------------------------------------------------------------
# Precedence chain
# ---------------------------------------------------------------------------

def test_env_var_overrides_config_json(tmp_path):
    cp = tmp_path / "config.json"
    cp.write_text(json.dumps({"model": "from-file"}))
    mgr = ConfigManager(config_path=cp, dotenv_path=tmp_path / ".env")
    env = {k: v for k, v in os.environ.items() if not k.startswith("DRAWING_COACH_")}
    env["DRAWING_COACH_MODEL"] = "from-env"
    with patch.dict("os.environ", env, clear=True):
        cfg = mgr.load()
    assert cfg.model == "from-env"


def test_dotenv_overrides_config_json(tmp_path):
    cp = tmp_path / "config.json"
    cp.write_text(json.dumps({"model": "from-file"}))
    dp = tmp_path / ".env"
    dp.write_text("DRAWING_COACH_MODEL=from-dotenv\n")
    mgr = ConfigManager(config_path=cp, dotenv_path=dp)
    env = {k: v for k, v in os.environ.items() if not k.startswith("DRAWING_COACH_")}
    with patch.dict("os.environ", env, clear=True):
        cfg = mgr.load()
    assert cfg.model == "from-dotenv"


def test_real_env_beats_dotenv(tmp_path):
    cp = tmp_path / "config.json"
    dp = tmp_path / ".env"
    dp.write_text("DRAWING_COACH_MODEL=from-dotenv\n")
    mgr = ConfigManager(config_path=cp, dotenv_path=dp)
    env = {k: v for k, v in os.environ.items() if not k.startswith("DRAWING_COACH_")}
    env["DRAWING_COACH_MODEL"] = "from-real-env"
    with patch.dict("os.environ", env, clear=True):
        cfg = mgr.load()
    assert cfg.model == "from-real-env"


def test_api_key_read_from_environ(tmp_path):
    mgr = make_manager(tmp_path)
    env = {k: v for k, v in os.environ.items() if not k.startswith("DRAWING_COACH_")}
    env["DRAWING_COACH_API_KEY"] = "sk-from-env"
    with patch.dict("os.environ", env, clear=True):
        cfg = mgr.load()
    assert cfg.api_key == "sk-from-env"


def test_api_key_empty_when_not_set(tmp_path):
    mgr = make_manager(tmp_path)
    env = {k: v for k, v in os.environ.items() if not k.startswith("DRAWING_COACH_")}
    with patch.dict("os.environ", env, clear=True):
        cfg = mgr.load()
    assert cfg.api_key == ""


# ---------------------------------------------------------------------------
# save() — persistence routing
# ---------------------------------------------------------------------------

def test_save_writes_preferences_to_config_json(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.load()
    cfg = LLMConfig(model="gpt-4o", capture_interval=60)
    mgr.save(cfg)
    data = json.loads((tmp_path / "config.json").read_text())
    assert data["model"] == "gpt-4o"
    assert data["capture_interval"] == 60


def test_save_excludes_api_key_from_config_json(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.load()
    cfg = LLMConfig(model="gpt-4o", api_key="sk-secret")
    mgr.save(cfg)
    data = json.loads((tmp_path / "config.json").read_text())
    assert "api_key" not in data


def test_save_writes_api_key_to_dotenv(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.load()
    cfg = LLMConfig(api_key="sk-test")
    with patch("drawing_coach.config_manager.set_key") as mock_set:
        mgr.save(cfg)
    mock_set.assert_called_once_with(str(tmp_path / ".env"), "DRAWING_COACH_API_KEY", "sk-test")


def test_save_removes_api_key_from_dotenv_when_empty(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.load()
    cfg = LLMConfig(api_key="")
    with patch("drawing_coach.config_manager.unset_key") as mock_unset:
        mgr.save(cfg)
    mock_unset.assert_called_once_with(str(tmp_path / ".env"), "DRAWING_COACH_API_KEY")


def test_save_updates_os_environ_with_api_key(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.load()
    cfg = LLMConfig(api_key="sk-new")
    env = {k: v for k, v in os.environ.items() if not k.startswith("DRAWING_COACH_")}
    with patch.dict("os.environ", env, clear=True):
        with patch("drawing_coach.config_manager.set_key"):
            mgr.save(cfg)
        assert os.environ.get("DRAWING_COACH_API_KEY") == "sk-new"


def test_save_clears_os_environ_when_api_key_empty(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.load()
    cfg = LLMConfig(api_key="")
    env = {k: v for k, v in os.environ.items() if not k.startswith("DRAWING_COACH_")}
    env["DRAWING_COACH_API_KEY"] = "old"
    with patch.dict("os.environ", env, clear=True):
        with patch("drawing_coach.config_manager.unset_key"):
            mgr.save(cfg)
        assert "DRAWING_COACH_API_KEY" not in os.environ


def test_save_raises_on_permission_error(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.load()
    cfg = LLMConfig(api_key="sk-x")
    with patch("drawing_coach.config_manager.set_key", side_effect=PermissionError("ro")):
        with pytest.raises(PermissionError, match="Could not save API key"):
            mgr.save(cfg)


# ---------------------------------------------------------------------------
# export / import portable
# ---------------------------------------------------------------------------

def test_export_excludes_api_key(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.load()
    mgr._config = LLMConfig(model="gpt-4o", api_key="sk-secret")
    out = tmp_path / "export.json"
    mgr.export_portable(out)
    data = json.loads(out.read_text())
    assert "api_key" not in data
    assert data["model"] == "gpt-4o"


def test_import_portable_returns_llmconfig(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.load()
    src = {"model": "claude-opus-4-8", "capture_interval": 45}
    src_path = tmp_path / "import.json"
    src_path.write_text(json.dumps(src))
    imported = mgr.import_portable(src_path)
    assert imported.model == "claude-opus-4-8"
    assert imported.capture_interval == 45


def test_import_portable_ignores_unknown_fields(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.load()
    src = {"model": "gpt-4o", "no_such_field": 99}
    src_path = tmp_path / "import.json"
    src_path.write_text(json.dumps(src))
    imported = mgr.import_portable(src_path)
    assert imported.model == "gpt-4o"


def test_export_import_round_trip(tmp_path):
    mgr = make_manager(tmp_path)
    mgr.load()
    mgr._config = LLMConfig(model="gpt-4o", capture_interval=90, api_key="sk-secret")
    out = tmp_path / "export.json"
    mgr.export_portable(out)
    imported = mgr.import_portable(out)
    assert imported.model == "gpt-4o"
    assert imported.capture_interval == 90
    assert imported.api_key == ""  # api_key never exported
