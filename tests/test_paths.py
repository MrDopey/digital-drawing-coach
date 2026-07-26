"""Unit tests for XDG-aware path resolution in drawing_coach.paths."""

from pathlib import Path
from unittest.mock import patch

import drawing_coach.paths as paths_mod
from drawing_coach.paths import (
    config_path,
    memory_path,
    memory_summaries_path,
    sessions_dir,
)


def test_config_path_xdg_config_home_set(tmp_path):
    with patch("drawing_coach.env.xdg_config_home", return_value=str(tmp_path)):
        with patch.object(paths_mod.sys, "platform", "linux"):
            assert config_path() == tmp_path / "drawing-coach" / "config.json"


def test_config_path_xdg_config_home_unset(tmp_path):
    with patch("drawing_coach.env.xdg_config_home", return_value=""):
        with patch.object(paths_mod.sys, "platform", "linux"):
            with patch.object(paths_mod.Path, "home", return_value=tmp_path):
                result = config_path()
    assert result == tmp_path / ".config" / "drawing-coach" / "config.json"


def test_sessions_dir_xdg_data_home_set(tmp_path):
    with patch("drawing_coach.env.xdg_data_home", return_value=str(tmp_path)):
        with patch.object(paths_mod.sys, "platform", "linux"):
            assert sessions_dir() == tmp_path / "drawing-coach" / "sessions"


def test_sessions_dir_xdg_data_home_unset(tmp_path):
    with patch("drawing_coach.env.xdg_data_home", return_value=""):
        with patch.object(paths_mod.sys, "platform", "linux"):
            with patch.object(paths_mod.Path, "home", return_value=tmp_path):
                result = sessions_dir()
    assert result == tmp_path / ".local/share" / "drawing-coach" / "sessions"


def test_config_path_windows(tmp_path):
    with patch.object(paths_mod.sys, "platform", "win32"):
        with patch.object(paths_mod.Path, "home", return_value=tmp_path):
            assert config_path() == tmp_path / ".drawing-coach" / "config.json"


def test_sessions_dir_windows(tmp_path):
    with patch.object(paths_mod.sys, "platform", "win32"):
        with patch.object(paths_mod.Path, "home", return_value=tmp_path):
            assert sessions_dir() == tmp_path / ".drawing-coach" / "sessions"


def test_memory_path_is_sibling_of_sessions_dir(tmp_path):
    with patch("drawing_coach.env.xdg_data_home", return_value=str(tmp_path)):
        with patch.object(paths_mod.sys, "platform", "linux"):
            assert memory_path() == tmp_path / "drawing-coach" / "memory.json"


def test_memory_summaries_path_is_sibling_of_sessions_dir(tmp_path):
    with patch("drawing_coach.env.xdg_data_home", return_value=str(tmp_path)):
        with patch.object(paths_mod.sys, "platform", "linux"):
            assert (
                memory_summaries_path()
                == tmp_path / "drawing-coach" / "memory_summaries.json"
            )
