"""Tests for the Settings dialog's LLM tab: debug logging checkbox and
Test Connection debug label."""

from unittest.mock import MagicMock, patch

from drawing_coach.hotkey_manager import HotkeyManager
from drawing_coach.llm_config import LLMConfig
from drawing_coach.settings_dialog import SettingsDialog


def _dialog(qtbot, config: LLMConfig) -> SettingsDialog:
    dlg = SettingsDialog(config=config, hotkey_manager=HotkeyManager())
    qtbot.addWidget(dlg)
    return dlg


def test_debug_log_checkbox_initialized_from_config(qtbot):
    dlg = _dialog(qtbot, LLMConfig(debug_log_llm_io=True))
    assert dlg._debug_log_checkbox.isChecked() is True

    dlg2 = _dialog(qtbot, LLMConfig(debug_log_llm_io=False))
    assert dlg2._debug_log_checkbox.isChecked() is False


def test_debug_log_checkbox_saved_into_config(qtbot):
    config = LLMConfig(model="gpt-4o", debug_log_llm_io=False)
    dlg = _dialog(qtbot, config)
    dlg._debug_log_checkbox.setChecked(True)
    dlg._apply_to_config()
    assert config.debug_log_llm_io is True


def test_test_connection_sends_debug_label(qtbot):
    config = LLMConfig(model="gpt-4o")
    dlg = _dialog(qtbot, config)
    dlg._model_edit.setText("gpt-4o")

    with patch("litellm.completion", return_value=MagicMock()) as mock_completion:
        dlg._test_connection()

    assert mock_completion.call_args.kwargs["metadata"] == {
        "debug_label": "settings_test_connection"
    }
