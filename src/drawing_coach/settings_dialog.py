from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
    QPushButton, QLabel, QHBoxLayout, QFileDialog, QMessageBox, QGroupBox,
    QTabWidget, QWidget,
)
from PyQt6.QtCore import Qt

from drawing_coach.llm_config import LLMConfig
from drawing_coach.hotkey_manager import HotkeyManager

# Common hotkeys known to conflict with drawing apps
_KNOWN_CONFLICTS = {"<ctrl>+z", "<ctrl>+s", "<ctrl>+c", "<ctrl>+v", "<ctrl>+a"}


class SettingsDialog(QDialog):
    def __init__(self, config: LLMConfig, hotkey_manager: HotkeyManager, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self._config = config
        self._hotkey_manager = hotkey_manager

        tabs = QTabWidget()
        tabs.addTab(self._build_llm_tab(), "LLM")
        tabs.addTab(self._build_capture_tab(), "Capture")
        tabs.addTab(self._build_stuck_tab(), "Stuck Detection")
        tabs.addTab(self._build_history_tab(), "History")

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("Save")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Tab builders
    # ------------------------------------------------------------------

    def _build_llm_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        form = QFormLayout()

        self._model_edit = QLineEdit(self._config.model)
        self._model_edit.setPlaceholderText("e.g. gpt-4o or ollama/llava")
        form.addRow("Model Name:", self._model_edit)

        self._key_edit = QLineEdit(self._config.api_key)
        self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_edit.setPlaceholderText("Leave blank for local models")
        form.addRow("API Key:", self._key_edit)

        self._base_edit = QLineEdit(self._config.api_base)
        self._base_edit.setPlaceholderText("e.g. http://localhost:11434 (optional)")
        form.addRow("Base URL:", self._base_edit)

        self._custom_edit = QLineEdit(self._config.custom_instructions)
        self._custom_edit.setPlaceholderText("Extra coaching instructions appended to every prompt")
        form.addRow("Custom Instructions:", self._custom_edit)

        layout.addLayout(form)

        test_row = QHBoxLayout()
        self._test_label = QLabel("")
        test_row.addWidget(self._test_label)
        test_row.addStretch()
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test_connection)
        test_row.addWidget(test_btn)
        layout.addLayout(test_row)

        export_row = QHBoxLayout()
        export_btn = QPushButton("Export Config…")
        export_btn.clicked.connect(self._export)
        import_btn = QPushButton("Import Config…")
        import_btn.clicked.connect(self._import)
        export_row.addWidget(export_btn)
        export_row.addWidget(import_btn)
        export_row.addStretch()
        layout.addLayout(export_row)
        layout.addStretch()
        return w

    def _build_capture_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(5, 300)
        self._interval_spin.setValue(self._config.capture_interval)
        self._interval_spin.setSuffix(" s")
        form.addRow("Capture Interval:", self._interval_spin)

        self._hotkey_edit = QLineEdit(self._config.hotkey)
        self._hotkey_edit.setPlaceholderText("<ctrl>+<shift>+f")
        self._hotkey_edit.textChanged.connect(self._check_hotkey_conflict)
        form.addRow("Feedback Hotkey:", self._hotkey_edit)

        self._conflict_label = QLabel("")
        self._conflict_label.setStyleSheet("color: orange;")
        form.addRow("", self._conflict_label)
        self._check_hotkey_conflict(self._config.hotkey)
        return w

    def _build_stuck_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self._threshold_spin = QDoubleSpinBox()
        self._threshold_spin.setRange(0.1, 100.0)
        self._threshold_spin.setSingleStep(0.5)
        self._threshold_spin.setValue(self._config.stuck_threshold)
        self._threshold_spin.setToolTip("Lower = more sensitive (default: 10.0)")
        form.addRow("MAE Threshold:", self._threshold_spin)

        self._consecutive_spin = QSpinBox()
        self._consecutive_spin.setRange(1, 20)
        self._consecutive_spin.setValue(self._config.stuck_consecutive)
        self._consecutive_spin.setToolTip("Number of consecutive low-change intervals before triggering (default: 3)")
        form.addRow("Consecutive Intervals:", self._consecutive_spin)

        self._cooldown_spin = QSpinBox()
        self._cooldown_spin.setRange(1, 60)
        self._cooldown_spin.setValue(self._config.stuck_cooldown_minutes)
        self._cooldown_spin.setSuffix(" min")
        self._cooldown_spin.setToolTip("Minimum time between automatic triggers (default: 5 min)")
        form.addRow("Cooldown Duration:", self._cooldown_spin)
        return w

    def _build_history_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)

        self._retention_spin = QSpinBox()
        self._retention_spin.setRange(1, 100)
        self._retention_spin.setValue(self._config.history_retention_sessions)
        self._retention_spin.setToolTip("Number of past sessions to keep on disk (default: 10)")
        form.addRow("Keep Last N Sessions:", self._retention_spin)

        self._dedup_spin = QDoubleSpinBox()
        self._dedup_spin.setRange(0.1, 50.0)
        self._dedup_spin.setSingleStep(0.5)
        self._dedup_spin.setValue(self._config.dedup_threshold)
        self._dedup_spin.setToolTip("MAE below this drops duplicate frames (default: 2.0; lower = more aggressive)")
        form.addRow("Dedup Threshold:", self._dedup_spin)

        self._lookback_spin = QSpinBox()
        self._lookback_spin.setRange(0, 10)
        self._lookback_spin.setValue(self._config.lookback_frames)
        self._lookback_spin.setToolTip("Prior history frames sent to LLM alongside the latest (default: 2; 0 = latest only)")
        form.addRow("Look-back Frames:", self._lookback_spin)
        return w

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _check_hotkey_conflict(self, text: str) -> None:
        if text.lower() in _KNOWN_CONFLICTS:
            self._conflict_label.setText(
                f"⚠ '{text}' is commonly used by drawing apps — consider a different hotkey."
            )
        else:
            self._conflict_label.setText("")

    def _test_connection(self) -> None:
        import litellm

        model = self._model_edit.text().strip()
        key = self._key_edit.text().strip()
        base = self._base_edit.text().strip()
        if not model:
            self._test_label.setText("Enter a model name first.")
            return
        self._test_label.setText("Testing…")
        try:
            kwargs: dict = {"model": model, "messages": [{"role": "user", "content": "hi"}]}
            if key:
                kwargs["api_key"] = key
            if base:
                kwargs["api_base"] = base
            litellm.completion(**kwargs)
            self._test_label.setText("✓ Connection successful")
            self._test_label.setStyleSheet("color: green;")
        except Exception as exc:
            self._test_label.setText(f"✗ {exc}")
            self._test_label.setStyleSheet("color: red;")

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Config", "drawing-coach-config.json", "JSON (*.json)"
        )
        if path:
            self._apply_to_config()
            self._config.export_portable(path)
            QMessageBox.information(self, "Exported", f"Config saved to {path} (API key excluded).")

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Config", "", "JSON (*.json)"
        )
        if not path:
            return
        imported = LLMConfig.import_portable(path)
        self._model_edit.setText(imported.model)
        self._base_edit.setText(imported.api_base)
        self._interval_spin.setValue(imported.capture_interval)
        self._hotkey_edit.setText(imported.hotkey)
        QMessageBox.information(
            self, "Imported", "Config loaded. Please re-enter your API key."
        )

    def _save(self) -> None:
        self._apply_to_config()
        self._config.save()
        new_hotkey = self._hotkey_edit.text().strip()
        if new_hotkey != self._hotkey_manager.hotkey:
            self._hotkey_manager.set_hotkey(new_hotkey)
        self.accept()

    def _apply_to_config(self) -> None:
        self._config.model = self._model_edit.text().strip()
        self._config.api_key = self._key_edit.text().strip()
        self._config.api_base = self._base_edit.text().strip()
        self._config.custom_instructions = self._custom_edit.text().strip()
        self._config.capture_interval = self._interval_spin.value()
        self._config.hotkey = self._hotkey_edit.text().strip()
        self._config.stuck_threshold = self._threshold_spin.value()
        self._config.stuck_consecutive = self._consecutive_spin.value()
        self._config.stuck_cooldown_minutes = self._cooldown_spin.value()
        self._config.history_retention_sessions = self._retention_spin.value()
        self._config.dedup_threshold = self._dedup_spin.value()
        self._config.lookback_frames = self._lookback_spin.value()
