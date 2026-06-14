"""Unit tests for XDG-aware path resolution in drawing_coach.paths."""

from pathlib import Path
from unittest.mock import patch

import drawing_coach.paths as paths_mod
from drawing_coach.paths import config_path, sessions_dir


def test_config_path_xdg_config_home_set(tmp_path):
    with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(tmp_path)}, clear=False):
        with patch.object(paths_mod.sys, "platform", "linux"):
            assert config_path() == tmp_path / "drawing-coach" / "config.json"


def test_config_path_xdg_config_home_unset(tmp_path):
    env = {"XDG_CONFIG_HOME": ""}
    with patch.dict("os.environ", env, clear=False):
        with patch.object(paths_mod.sys, "platform", "linux"):
            with patch.object(paths_mod.Path, "home", return_value=tmp_path):
                result = config_path()
    assert result == tmp_path / ".config" / "drawing-coach" / "config.json"


def test_sessions_dir_xdg_data_home_set(tmp_path):
    with patch.dict("os.environ", {"XDG_DATA_HOME": str(tmp_path)}, clear=False):
        with patch.object(paths_mod.sys, "platform", "linux"):
            assert sessions_dir() == tmp_path / "drawing-coach" / "sessions"


def test_sessions_dir_xdg_data_home_unset(tmp_path):
    env = {"XDG_DATA_HOME": ""}
    with patch.dict("os.environ", env, clear=False):
        with patch.object(paths_mod.sys, "platform", "linux"):
            with patch.object(paths_mod.Path, "home", return_value=tmp_path):
                result = sessions_dir()
    assert result == tmp_path / ".local" / "share" / "drawing-coach" / "sessions"


def test_config_path_windows(tmp_path):
    with patch.object(paths_mod.sys, "platform", "win32"):
        with patch.object(paths_mod.Path, "home", return_value=tmp_path):
            assert config_path() == tmp_path / ".drawing-coach" / "config.json"


def test_sessions_dir_windows(tmp_path):
    with patch.object(paths_mod.sys, "platform", "win32"):
        with patch.object(paths_mod.Path, "home", return_value=tmp_path):
            assert sessions_dir() == tmp_path / ".drawing-coach" / "sessions"
