from __future__ import annotations

import io
import json
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from drawing_coach import perf
from drawing_coach.design_system import MutedLabel, PillBadge
from drawing_coach.llm_config import LLMConfig
from drawing_coach.paths import config_path, sessions_dir


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    hint: str = field(default="")


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------


def check_screen_capture() -> CheckResult:
    name = "Screen Capture"
    if sys.platform == "darwin":
        try:
            from drawing_coach._backend_macos import has_screen_recording_permission

            if has_screen_recording_permission():
                return CheckResult(name, True, "Screen Recording permission granted")
            return CheckResult(
                name,
                False,
                "Screen Recording permission denied",
                "Open System Settings → Privacy & Security → Screen Recording and enable Drawing Coach",
            )
        except Exception as exc:
            return CheckResult(name, False, f"Could not check: {exc}")
    else:
        try:
            import mss

            with mss.mss() as sct:
                sct.grab(sct.monitors[0])
            return CheckResult(name, True, "Screen capture available")
        except Exception as exc:
            return CheckResult(
                name,
                False,
                str(exc),
                "Ensure a display server (X11 or Wayland) is running and the app has display access",
            )


def check_accessibility() -> CheckResult:
    name = "Accessibility"
    try:
        from drawing_coach._backend_macos import has_accessibility_permission

        if has_accessibility_permission():
            return CheckResult(name, True, "Accessibility permission granted")
        return CheckResult(
            name,
            False,
            "Accessibility permission denied",
            "Open System Settings → Privacy & Security → Accessibility and enable Drawing Coach",
        )
    except Exception as exc:
        return CheckResult(name, False, f"Could not check: {exc}")


def check_input_monitoring() -> CheckResult:
    name = "Input Monitoring"
    try:
        from drawing_coach._backend_macos import has_input_monitoring_permission

        if has_input_monitoring_permission():
            return CheckResult(name, True, "Input Monitoring permission granted")
        return CheckResult(
            name,
            False,
            "Input Monitoring permission denied",
            "Open System Settings → Privacy & Security → Input Monitoring and enable Drawing Coach;"
            " hotkeys will not work without this",
        )
    except Exception as exc:
        return CheckResult(name, False, f"Could not check: {exc}")


def check_xdotool() -> CheckResult:
    name = "xdotool"
    if shutil.which("xdotool") is not None:
        return CheckResult(name, True, "xdotool found")
    return CheckResult(
        name,
        False,
        "xdotool not found",
        "Install xdotool (e.g. sudo apt install xdotool) — without it no drawing windows can be detected",
    )


def check_llm(config: LLMConfig) -> CheckResult:
    name = "LLM Connection"
    if not config.model:
        return CheckResult(
            name,
            False,
            "No model configured",
            "Open Settings → LLM tab and enter a model name (e.g. gpt-4o or ollama/llava)",
        )
    try:
        import litellm

        kwargs: dict = {
            "model": config.model,
            "messages": [{"role": "user", "content": "hi"}],
            "metadata": {"debug_label": "diagnostics_check_llm"},
        }
        if config.api_key:
            kwargs["api_key"] = config.api_key
        if config.api_base:
            kwargs["api_base"] = config.api_base
        litellm.completion(**kwargs)
        return CheckResult(name, True, "LLM connection successful (text completion)")
    except Exception as exc:
        return CheckResult(
            name,
            False,
            f"{type(exc).__name__}: {exc}",
            "Check your API key, Base URL, and network connection in Settings → LLM",
        )


def check_config_path() -> CheckResult:
    name = "Config Access"
    p = config_path()
    config_dir = p.parent
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    if not os.access(config_dir, os.W_OK):
        return CheckResult(
            name,
            False,
            f"Config directory not writable: {config_dir}",
            f"Check file permissions on {config_dir} or run the app as a user with write access",
        )
    if p.exists():
        try:
            json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return CheckResult(
                name,
                False,
                f"Config file is corrupt: {p}",
                f"The config file at {p} is corrupt — delete it to reset to defaults",
            )
    return CheckResult(name, True, f"Config accessible: {p}")


def check_sessions_dir() -> CheckResult:
    name = "Sessions Directory"
    d = sessions_dir()
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return CheckResult(
            name,
            False,
            f"Cannot create sessions directory: {exc}",
            f"Check permissions on {d.parent} or set XDG_DATA_HOME to a writable directory",
        )
    probe = d / ".diag_probe"
    try:
        probe.write_text("ok")
        probe.unlink()
    except OSError:
        return CheckResult(
            name,
            False,
            f"Sessions directory not writable: {d}",
            f"Check permissions on {d.parent} or set XDG_DATA_HOME to a writable directory",
        )
    return CheckResult(name, True, f"Sessions directory accessible: {d}")


def check_pillow_png() -> CheckResult:
    name = "Pillow PNG"
    try:
        from PIL import Image

        Image.new("RGB", (1, 1)).save(io.BytesIO(), "PNG")
        return CheckResult(name, True, "Pillow PNG codec available")
    except Exception as exc:
        return CheckResult(
            name,
            False,
            str(exc),
            "Reinstall Pillow: uv pip install --reinstall Pillow",
        )


def build_checks(config: LLMConfig) -> list[tuple[str, Callable[[], CheckResult]]]:
    checks: list[tuple[str, Callable[[], CheckResult]]] = [
        ("Screen Capture", check_screen_capture),
    ]
    if sys.platform == "darwin":
        checks.append(("Accessibility", check_accessibility))
        checks.append(("Input Monitoring", check_input_monitoring))
    elif sys.platform == "linux":
        checks.append(("xdotool", check_xdotool))
    checks += [
        ("LLM Connection", lambda: check_llm(config)),
        ("Config Access", check_config_path),
        ("Sessions Directory", check_sessions_dir),
        ("Pillow PNG", check_pillow_png),
    ]
    return checks


# ---------------------------------------------------------------------------
# Qt worker and dialog
# ---------------------------------------------------------------------------


class DiagnosticsCoordinator(QThread):
    check_done = pyqtSignal(object)
    all_done = pyqtSignal()

    def __init__(
        self,
        executor: ThreadPoolExecutor,
        futures: list,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._executor = executor
        self._futures = futures

    def run(self) -> None:
        for future in as_completed(self._futures):
            try:
                result = future.result()
                if result is not None:
                    self.check_done.emit(result)
            except Exception:
                pass
        self.all_done.emit()


class DiagnosticsDialog(QDialog):
    def __init__(self, config: LLMConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("System Diagnostics")
        self.setMinimumWidth(580)
        self._config = config
        self._checks = build_checks(config)
        self._executor: ThreadPoolExecutor | None = None
        self._coordinator: DiagnosticsCoordinator | None = None
        self._completed_results: list[CheckResult] = []

        layout = QVBoxLayout(self)

        rows_widget = QWidget()
        grid = QGridLayout(rows_widget)
        grid.setColumnMinimumWidth(0, 28)
        grid.setColumnMinimumWidth(1, 170)
        grid.setColumnStretch(2, 1)
        grid.setVerticalSpacing(2)
        grid.setHorizontalSpacing(10)
        grid.setContentsMargins(8, 8, 8, 8)

        self._status_labels: dict[str, QLabel] = {}
        self._msg_labels: dict[str, QLabel] = {}
        self._hint_labels: dict[str, QLabel] = {}

        _selectable = (
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )

        for row_idx, (name, _) in enumerate(self._checks):
            grid_row = row_idx * 2
            status_lbl = PillBadge("⏳")
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
            name_lbl = QLabel(f"<b>{name}</b>")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
            msg_lbl = PillBadge("checking…")
            msg_lbl.setWordWrap(True)
            msg_lbl.setTextFormat(Qt.TextFormat.RichText)
            msg_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
            msg_lbl.setMinimumWidth(1)
            msg_lbl.setTextInteractionFlags(_selectable)

            hint_lbl = MutedLabel(
                "", extra_style="padding-left: 2px; padding-bottom: 6px;"
            )
            hint_lbl.setWordWrap(True)
            hint_lbl.setTextFormat(Qt.TextFormat.RichText)
            hint_lbl.setMinimumWidth(1)
            hint_lbl.setTextInteractionFlags(_selectable)
            hint_lbl.setVisible(False)

            grid.addWidget(status_lbl, grid_row, 0)
            grid.addWidget(name_lbl, grid_row, 1)
            grid.addWidget(msg_lbl, grid_row, 2)
            grid.addWidget(hint_lbl, grid_row + 1, 1, 1, 2)

            self._status_labels[name] = status_lbl
            self._msg_labels[name] = msg_lbl
            self._hint_labels[name] = hint_lbl

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(rows_widget)
        layout.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        self._rerun_btn = QPushButton("Re-run")
        self._rerun_btn.clicked.connect(self._start_checks)
        self._copy_report_btn = QPushButton("Copy Report")
        self._copy_report_btn.clicked.connect(self._copy_report)
        self._copy_report_btn.setEnabled(False)
        # Only meaningful during an instrumented run, so it stays out of the
        # way entirely on a normal one.
        self._copy_perf_btn = QPushButton("Copy Perf Snapshot")
        self._copy_perf_btn.clicked.connect(self._copy_perf_snapshot)
        self._copy_perf_btn.setVisible(perf.ON)
        btn_row.addStretch()
        btn_row.addWidget(self._copy_perf_btn)
        btn_row.addWidget(self._copy_report_btn)
        btn_row.addWidget(self._rerun_btn)
        layout.addLayout(btn_row)

        self._start_checks()
        self.adjustSize()

    def _start_checks(self) -> None:
        if self._coordinator and self._coordinator.isRunning():
            if self._executor:
                self._executor.shutdown(wait=False, cancel_futures=True)
            self._coordinator.wait()

        self._completed_results = []

        for name in self._status_labels:
            self._status_labels[name].setText("⏳")
            self._status_labels[name].set_variant("neutral")
            self._msg_labels[name].setText("checking…")
            self._msg_labels[name].set_variant("neutral")
            self._hint_labels[name].setText("")
            self._hint_labels[name].setVisible(False)

        self._rerun_btn.setEnabled(False)
        self._copy_report_btn.setEnabled(False)

        self._executor = ThreadPoolExecutor(max_workers=len(self._checks))
        futures = [self._executor.submit(fn) for _, fn in self._checks]

        self._coordinator = DiagnosticsCoordinator(self._executor, futures, parent=self)
        self._coordinator.check_done.connect(self._on_check_done)
        self._coordinator.all_done.connect(self._on_all_done)
        self._coordinator.start()

    def _on_all_done(self) -> None:
        self._rerun_btn.setEnabled(True)
        self._copy_report_btn.setEnabled(True)

    def _on_check_done(self, result: CheckResult) -> None:
        self._completed_results.append(result)
        status_lbl = self._status_labels.get(result.name)
        msg_lbl = self._msg_labels.get(result.name)
        hint_lbl = self._hint_labels.get(result.name)
        if status_lbl is None or msg_lbl is None:
            return
        if result.passed:
            status_lbl.setText("✓")
            status_lbl.set_variant("success")
            msg_lbl.setText(result.message)
            msg_lbl.set_variant("neutral")
            if hint_lbl:
                hint_lbl.setVisible(False)
        else:
            status_lbl.setText("✗")
            status_lbl.set_variant("danger")
            msg_lbl.setText(result.message)
            msg_lbl.set_variant("danger")
            if hint_lbl and result.hint:
                hint_lbl.setText(result.hint)
                hint_lbl.setVisible(True)
            elif hint_lbl:
                hint_lbl.setVisible(False)

    def _copy_perf_snapshot(self) -> None:
        QApplication.clipboard().setText(perf.snapshot())

    def _copy_report(self) -> None:
        lines: list[str] = []
        for result in self._completed_results:
            icon = "✓" if result.passed else "✗"
            lines.append(f"[{icon}] {result.name} — {result.message}")
            if not result.passed and result.hint:
                lines.append(f"      Hint: {result.hint}")
        QApplication.clipboard().setText("\n".join(lines))

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
        if self._coordinator and self._coordinator.isRunning():
            self._coordinator.quit()
            self._coordinator.wait()
        super().closeEvent(event)
