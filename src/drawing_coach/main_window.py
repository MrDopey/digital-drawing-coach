from __future__ import annotations

import platform
import threading
from pathlib import Path

from PIL import Image as PilImage
from PyQt6.QtCore import QObject, QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QCloseEvent, QColor, QIcon, QPainter, QPen, QPixmap, QPolygon
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from drawing_coach._version import __version__
from drawing_coach.app_selection_dialog import AppSelectionDialog
from drawing_coach.capture_engine import CapturedFrame, CaptureEngine
from drawing_coach.feedback_engine import FeedbackEngine, FeedbackResponse
from drawing_coach.feedback_panel import FeedbackPanel
from drawing_coach.history_panel import HistoryPanel
from drawing_coach.hotkey_manager import HotkeyManager
from drawing_coach.config_manager import ConfigManager
from drawing_coach.llm_config import LLMConfig
from drawing_coach.overlay_renderer import render as render_overlay
from drawing_coach.settings_dialog import SettingsDialog
from drawing_coach.stuck_detector import StuckDetector
from drawing_coach.window_manager import WindowManager

_STYLE_PRESETS = [
    "",  # blank = "General"
    "Line Drawing",
    "Realistic",
    "Anime/Manga",
    "Chibi",
    "Concept Art",
    "Portrait",
]


class _WriteErrorPopup(QFrame):
    """Borderless floating popup that shows the full write-error detail."""

    def __init__(self, label: "_WriteErrorLabel") -> None:
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._label = label
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self._text.setFrameShape(QFrame.Shape.NoFrame)
        self._text.setFixedWidth(480)
        layout.addWidget(self._text)
        self.setStyleSheet(
            "_WriteErrorPopup { background: #fffde7; border: 1px solid #f9a825; }"
        )

    def set_body(self, text: str) -> None:
        self._text.setPlainText(text)
        self._text.document().adjustSize()
        doc_h = int(self._text.document().size().height()) + 24
        self._text.setFixedHeight(min(doc_h, 220))
        self.adjustSize()

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._label._cancel_hide()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._label._schedule_hide()
        super().leaveEvent(event)


class _WriteErrorLabel(QLabel):
    """Status-bar label for write failures — selectable text, hover popup."""

    def __init__(self) -> None:
        super().__init__()
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.setStyleSheet("color: #d97706;")
        self._popup = _WriteErrorPopup(self)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(150)
        self._hide_timer.timeout.connect(self._popup.hide)

    def set_error(self, path: Path, exc: Exception) -> None:
        self.setText("⚠ Frame saves failing — images will be lost if the app closes.")
        body = (
            f"Frame write failed: {path}\n"
            f"Error: {exc}\n\n"
            f"To fix:\n"
            f"• Ensure this directory is writable:\n"
            f"    {path.parent}\n"
            f"• Check available disk space.\n"
            f"• On macOS, check System Settings → Privacy & Security → Files and Folders."
        )
        self._popup.set_body(body)

    def clear_error(self) -> None:
        self.clear()
        self._popup.hide()

    def _schedule_hide(self) -> None:
        self._hide_timer.start()

    def _cancel_hide(self) -> None:
        self._hide_timer.stop()

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._cancel_hide()
        if self.text():
            pos = self.mapToGlobal(QPoint(0, 0))
            popup_h = self._popup.sizeHint().height()
            self._popup.move(pos.x(), pos.y() - popup_h - 4)
            self._popup.show()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._schedule_hide()
        super().leaveEvent(event)


class _Signals(QObject):
    feedback_ready = pyqtSignal(object, object)  # FeedbackResponse, overlay_image|None
    feedback_error = pyqtSignal(str)
    window_lost = pyqtSignal()
    frame_captured = pyqtSignal()
    write_error = pyqtSignal(str, str)  # path_str, exc_str
    write_error_clear = pyqtSignal()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Drawing Coach")
        self.setMinimumSize(460, 300)

        self._config_manager = ConfigManager()
        self._config = self._config_manager.load()
        self._manager = WindowManager()
        self._capture = CaptureEngine(self._manager, config=self._config)
        self._detector = StuckDetector(
            threshold=self._config.stuck_threshold,
            consecutive_count=self._config.stuck_consecutive,
            cooldown_seconds=self._config.stuck_cooldown_minutes * 60,
        )
        self._hotkeys = HotkeyManager()
        self._feedback_engine = FeedbackEngine(self._config)
        self._feedback_panel = FeedbackPanel()
        self._signals = _Signals()

        self._setup_callbacks()
        self._build_ui()
        self._build_tray()
        self._hotkeys.set_hotkey(self._config.hotkey)
        self._hotkeys.start()

        self._capture.interval = self._config.capture_interval
        self._capture.start()

        self._signals.feedback_ready.connect(self._on_feedback_ready)
        self._signals.feedback_error.connect(self._feedback_panel.show_error)
        self._signals.window_lost.connect(self._on_window_lost)
        self._signals.frame_captured.connect(self._update_status)
        self._signals.write_error.connect(self._on_write_error_main)
        self._signals.write_error_clear.connect(self._write_error_label.clear_error)

        if not self._config.is_configured():
            QTimer.singleShot(200, self._run_onboarding)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self._window_label = QLabel("No drawing window selected")
        self._window_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._window_label)

        self._status_label = QLabel("Capture: stopped")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        # Coaching style row
        style_row = QHBoxLayout()
        style_row.addWidget(QLabel("Style:"))
        self._style_combo = QComboBox()
        self._style_combo.addItem("General", "")
        for preset in _STYLE_PRESETS[1:]:
            self._style_combo.addItem(preset, preset)
        # Pre-select saved value
        if self._config.style_focus and self._config.style_focus_is_preset:
            idx = self._style_combo.findData(self._config.style_focus)
            if idx >= 0:
                self._style_combo.setCurrentIndex(idx)
        self._style_combo.currentIndexChanged.connect(self._on_preset_selected)
        style_row.addWidget(self._style_combo)

        self._focus_edit = QLineEdit()
        self._focus_edit.setPlaceholderText(
            "or type custom focus e.g. 'gothic pokemon'"
        )
        self._focus_edit.setMaxLength(200)
        if self._config.style_focus and not self._config.style_focus_is_preset:
            self._focus_edit.setText(self._config.style_focus)
        self._focus_edit.textEdited.connect(self._on_focus_text_edited)
        style_row.addWidget(self._focus_edit, 1)
        layout.addLayout(style_row)

        self._coaching_label = QLabel(
            f"Coaching for: {self._config.effective_style_label()}"
        )
        self._coaching_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._coaching_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._coaching_label)

        btn_row = QHBoxLayout()
        self._select_btn = QPushButton("Select Window")
        self._select_btn.clicked.connect(self._open_app_selection)
        btn_row.addWidget(self._select_btn)

        self._pause_btn = QPushButton("Pause")
        self._pause_btn.clicked.connect(self._toggle_pause)
        btn_row.addWidget(self._pause_btn)

        feedback_btn = QPushButton("Get Feedback")
        feedback_btn.clicked.connect(self._trigger_feedback)
        btn_row.addWidget(feedback_btn)

        history_btn = QPushButton("History")
        history_btn.clicked.connect(self._open_history)
        btn_row.addWidget(history_btn)

        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self._open_settings)
        btn_row.addWidget(settings_btn)

        layout.addLayout(btn_row)

        self._write_error_label = _WriteErrorLabel()
        self.statusBar().addPermanentWidget(self._write_error_label, 1)
        self.statusBar().setSizeGripEnabled(False)

    def _build_tray(self) -> None:
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(self._make_tray_icon())
        self._tray.setToolTip("Drawing Coach")
        menu = QMenu()
        menu.addAction("Get Feedback", self._trigger_feedback)
        menu.addSeparator()
        self._tray_pause_action = QAction("Pause Capture", self)
        self._tray_pause_action.triggered.connect(self._toggle_pause)
        menu.addAction(self._tray_pause_action)
        menu.addAction("Settings", self._open_settings)
        menu.addSeparator()
        menu.addAction(f"About (v{__version__})", self._show_about)
        menu.addAction("Quit", QApplication.quit)
        self._tray.setContextMenu(menu)
        self._tray.show()

    @staticmethod
    def _make_tray_icon() -> QIcon:
        px = QPixmap(22, 22)
        px.fill(QColor(0, 0, 0, 0))
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Pencil pointing bottom-right (like writing), drawn vertically then rotated 45°
        p.translate(11, 11)
        p.rotate(45)

        # Eraser (pink)
        p.setBrush(QColor("#FF9999"))
        p.setPen(QPen(QColor("#CC6666"), 0.5))
        p.drawRect(-3, -10, 6, 3)

        # Ferrule (silver band)
        p.setBrush(QColor("#C8C8C8"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(-3, -7, 6, 2)

        # Body (yellow)
        p.setBrush(QColor("#FFD700"))
        p.setPen(QPen(QColor("#B8860B"), 0.5))
        p.drawRect(-3, -5, 6, 10)

        # Wood taper
        p.setBrush(QColor("#DEB887"))
        p.setPen(QPen(QColor("#A0522D"), 0.5))
        p.drawPolygon(QPolygon([QPoint(-3, 5), QPoint(3, 5), QPoint(2, 8), QPoint(-2, 8)]))

        # Graphite tip
        p.setBrush(QColor("#444444"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(QPolygon([QPoint(-2, 8), QPoint(2, 8), QPoint(0, 10)]))

        p.end()
        return QIcon(px)

    # ------------------------------------------------------------------
    # Style / focus handlers
    # ------------------------------------------------------------------

    def _on_preset_selected(self, _: int) -> None:
        preset = self._style_combo.currentData()
        if preset:
            self._focus_edit.clear()
            self._config.style_focus = preset
            self._config.style_focus_is_preset = True
        else:
            self._config.style_focus = ""
            self._config.style_focus_is_preset = True
        self._coaching_label.setText(
            f"Coaching for: {self._config.effective_style_label()}"
        )
        self._config_manager.save(self._config)

    def _on_focus_text_edited(self, text: str) -> None:
        text = text.strip()
        if len(text) > 200:
            text = text[:200]
            self._focus_edit.setText(text)
        if text:
            # deselect preset
            self._style_combo.blockSignals(True)
            self._style_combo.setCurrentIndex(0)
            self._style_combo.blockSignals(False)
            self._config.style_focus = text
            self._config.style_focus_is_preset = False
        else:
            self._config.style_focus = ""
            self._config.style_focus_is_preset = True
        self._coaching_label.setText(
            f"Coaching for: {self._config.effective_style_label()}"
        )
        self._config_manager.save(self._config)

    # ------------------------------------------------------------------
    # Callbacks / signals
    # ------------------------------------------------------------------

    def _setup_callbacks(self) -> None:
        self._capture.on_frame_captured = self._on_frame_captured
        self._capture.on_window_lost = lambda: self._signals.window_lost.emit()
        self._capture.on_write_error = self._on_write_error
        self._detector.on_stuck = self._trigger_feedback
        self._hotkeys.on_trigger = lambda: self._detector.manual_trigger()

    def _on_frame_captured(self, frame: CapturedFrame) -> None:
        if frame.path is not None:
            self._signals.write_error_clear.emit()
        self._detector.feed(frame)
        self._signals.frame_captured.emit()

    def _on_write_error(self, path: Path, exc: Exception) -> None:
        # Called from capture thread — marshal to main thread via signal.
        self._signals.write_error.emit(str(path), str(exc))

    def _on_write_error_main(self, path_str: str, exc_str: str) -> None:
        self._write_error_label.set_error(Path(path_str), Exception(exc_str))

    def _on_feedback_ready(
        self, response: FeedbackResponse, overlay_image: PilImage.Image | None
    ) -> None:
        self._feedback_panel.show_feedback(response, overlay_image)

    def _on_window_lost(self) -> None:
        self._capture.pause()
        self._update_status()
        QMessageBox.warning(
            self,
            "Window Closed",
            "The drawing window was closed. Select a new window to resume capture.",
        )
        self._open_app_selection()

    def _update_status(self) -> None:
        if self._capture.target:
            self._window_label.setText(f"Monitoring: {self._capture.target.title}")
        if self._capture.paused:
            self._status_label.setText("Capture: paused")
            self._pause_btn.setText("Resume")
            self._tray_pause_action.setText("Resume Capture")
        else:
            frames = len(self._capture.get_frames())
            self._status_label.setText(f"Capture: active  ({frames} frames)")
            self._pause_btn.setText("Pause")
            self._tray_pause_action.setText("Pause Capture")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _open_app_selection(self) -> None:
        dlg = AppSelectionDialog(self._manager, self)
        if dlg.exec() and dlg.selected_window:
            self._capture.set_target(dlg.selected_window)
            self._capture.resume()
            self._update_status()

    def _toggle_pause(self) -> None:
        if self._capture.paused:
            self._capture.resume()
        else:
            self._capture.pause()
        self._update_status()

    def _trigger_feedback(self) -> None:
        if not self._config.is_configured():
            QMessageBox.information(
                self,
                "LLM Not Configured",
                "No LLM configured — open Settings to add your model details.",
            )
            return
        self._feedback_panel.show_loading()
        mode = self._feedback_panel.current_mode()
        frames = self._capture.get_frames()
        latest_image = frames[-1].image if frames else None

        def _run() -> None:
            result = self._feedback_engine.request_feedback(frames, mode)
            if isinstance(result, FeedbackResponse):
                overlay_image = None
                if mode == "overlay" and result.annotation_json and latest_image:
                    rendered, err = render_overlay(latest_image, result.annotation_json)
                    overlay_image = rendered if err is None else None
                    if err:
                        result = FeedbackResponse(
                            mode=result.mode,
                            text=result.text + f"\n\n*{err}*",
                            annotation_json=None,
                        )
                self._signals.feedback_ready.emit(result, overlay_image)
            else:
                self._signals.feedback_error.emit(result)

        threading.Thread(target=_run, daemon=True).start()

    def _open_history(self) -> None:
        dlg = HistoryPanel(self._capture.get_frames(), self)
        dlg.exec()

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._config, self._hotkeys, self, self._config_manager)
        if dlg.exec():
            self._capture.interval = self._config.capture_interval
            self._detector.threshold = self._config.stuck_threshold
            self._detector.consecutive_count = self._config.stuck_consecutive
            self._detector.cooldown_seconds = self._config.stuck_cooldown_minutes * 60
            self._capture.apply_retention(self._config.history_retention_sessions)

    def _run_onboarding(self) -> None:
        QMessageBox.information(
            self,
            "Welcome to Drawing Coach",
            "To get started:\n\n"
            "1. Open Settings and configure your LLM (model name + API key).\n"
            "2. Click 'Select Window' to choose your drawing application.\n"
            "3. Drawing Coach will capture screenshots and coach you automatically.\n\n"
            "Press Ctrl+Shift+F at any time to request feedback manually."
            + (
                "\n\n⚠ On macOS, you'll need to grant Screen Recording permission.\n"
                "Go to System Settings → Privacy & Security → Screen Recording."
                if platform.system() == "Darwin"
                else ""
            ),
        )
        self._open_settings()

    def _show_about(self) -> None:
        QMessageBox.about(
            self, "Drawing Coach", f"Drawing Coach\nVersion {__version__}"
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        event.ignore()
        self.hide()
        self._tray.showMessage(
            "Drawing Coach",
            "Still running in the background. Right-click the tray icon to quit.",
            QSystemTrayIcon.MessageIcon.Information,
            2000,
        )
