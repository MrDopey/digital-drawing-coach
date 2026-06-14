"""Unit tests for drawing_coach.env — the sole os.environ reader."""

from unittest.mock import patch

import drawing_coach.env as env_mod


def test_api_key_returns_env_var():
    with patch.dict("os.environ", {"DRAWING_COACH_API_KEY": "sk-test"}):
        assert env_mod.api_key() == "sk-test"


def test_api_key_returns_empty_when_absent():
    with patch.dict("os.environ", {}, clear=False):
        env = {k: v for k, v in __import__("os").environ.items() if k != "DRAWING_COACH_API_KEY"}
        with patch.dict("os.environ", env, clear=True):
            assert env_mod.api_key() == ""


def test_model_returns_env_var():
    with patch.dict("os.environ", {"DRAWING_COACH_MODEL": "gpt-4o"}):
        assert env_mod.model() == "gpt-4o"


def test_model_returns_empty_when_absent():
    with patch.dict("os.environ", {"DRAWING_COACH_MODEL": ""}, clear=False):
        assert env_mod.model() == ""


def test_api_base_returns_env_var():
    with patch.dict("os.environ", {"DRAWING_COACH_API_BASE": "http://localhost:11434"}):
        assert env_mod.api_base() == "http://localhost:11434"


def test_api_base_returns_empty_when_absent():
    with patch.dict("os.environ", {"DRAWING_COACH_API_BASE": ""}, clear=False):
        assert env_mod.api_base() == ""


def test_xdg_config_home_returns_env_var(tmp_path):
    with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(tmp_path)}):
        assert env_mod.xdg_config_home() == str(tmp_path)


def test_xdg_config_home_returns_empty_when_absent():
    with patch.dict("os.environ", {"XDG_CONFIG_HOME": ""}, clear=False):
        assert env_mod.xdg_config_home() == ""


def test_xdg_data_home_returns_env_var(tmp_path):
    with patch.dict("os.environ", {"XDG_DATA_HOME": str(tmp_path)}):
        assert env_mod.xdg_data_home() == str(tmp_path)


def test_xdg_data_home_returns_empty_when_absent():
    with patch.dict("os.environ", {"XDG_DATA_HOME": ""}, clear=False):
        assert env_mod.xdg_data_home() == ""
