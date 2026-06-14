"""Unit tests for drawing_coach.env — XDG path helpers and operational env vars."""

from unittest.mock import patch

import drawing_coach.env as env_mod


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


def test_log_level_returns_env_var():
    with patch.dict("os.environ", {"DRAWING_COACH_LOG_LEVEL": "DEBUG"}):
        assert env_mod.log_level() == "DEBUG"


def test_log_level_returns_empty_when_absent():
    with patch.dict("os.environ", {"DRAWING_COACH_LOG_LEVEL": ""}, clear=False):
        assert env_mod.log_level() == ""


def test_log_file_returns_env_var(tmp_path):
    with patch.dict("os.environ", {"DRAWING_COACH_LOG_FILE": str(tmp_path / "app.log")}):
        assert env_mod.log_file() == str(tmp_path / "app.log")


def test_log_file_returns_empty_when_absent():
    with patch.dict("os.environ", {"DRAWING_COACH_LOG_FILE": ""}, clear=False):
        assert env_mod.log_file() == ""


def test_log_max_bytes_returns_env_var():
    with patch.dict("os.environ", {"DRAWING_COACH_LOG_MAX_BYTES": "5000000"}):
        assert env_mod.log_max_bytes() == "5000000"


def test_log_max_bytes_returns_empty_when_absent():
    with patch.dict("os.environ", {"DRAWING_COACH_LOG_MAX_BYTES": ""}, clear=False):
        assert env_mod.log_max_bytes() == ""
