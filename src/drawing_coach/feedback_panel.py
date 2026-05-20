from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QComboBox, QFileDialog, QStackedWidget,
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QMouseEvent, QPixmap, QImage

from drawing_coach.feedback_engine import FeedbackResponse

MODE_LABELS = {
    "quick_hint": "Quick Hint",
    "full_critique": "Full Critique",
    "practice_exercise": "Practice Exercise",
    "overlay": "Overlay",
}


def _pil_to_pixmap(img) -> QPixmap:
    from PIL import Image
    rgb = img.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    qimg = QImage(data, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg)


class FeedbackPanel(QWidget):
    """Floating, draggable panel that shows LLM feedback."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("Drawing Coach — Feedback")
        self.setMinimumSize(380, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(
            "QWidget { background: #1e1e1e; color: #e0e0e0; }"
            "QTextEdit { background: #252525; border: none; }"
            "QPushButton { background: #333; border-radius: 4px; padding: 4px 10px; }"
            "QPushButton:hover { background: #444; }"
        )

        self._drag_pos: QPoint | None = None
        self._history: list[FeedbackResponse] = []
        self._history_idx: int = -1
        self._overlay_images: dict[int, object] = {}   # idx → PIL Image

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Title bar
        title_row = QHBoxLayout()
        title_label = QLabel("Drawing Coach")
        title_label.setStyleSheet("font-weight: bold;")
        title_row.addWidget(title_label)
        title_row.addStretch()
        dismiss_btn = QPushButton("✕")
        dismiss_btn.setFixedSize(24, 24)
        dismiss_btn.clicked.connect(self.hide)
        title_row.addWidget(dismiss_btn)
        layout.addLayout(title_row)

        # Mode selector
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self._mode_combo = QComboBox()
        for key, label in MODE_LABELS.items():
            self._mode_combo.addItem(label, key)
        mode_row.addWidget(self._mode_combo)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # Loading indicator
        self._loading_label = QLabel("Thinking…")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.hide()
        layout.addWidget(self._loading_label)

        # Content stack: text vs image
        self._stack = QStackedWidget()
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._stack.addWidget(self._text_edit)       # index 0

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setScaledContents(False)
        self._stack.addWidget(self._image_label)     # index 1
        layout.addWidget(self._stack)

        # Overlay save row (shown only in overlay mode)
        self._save_row = QHBoxLayout()
        self._overlay_notice = QLabel("")
        self._overlay_notice.setStyleSheet("color: #aaa; font-size: 11px;")
        self._save_row.addWidget(self._overlay_notice)
        self._save_row.addStretch()
        self._save_btn = QPushButton("Save Overlay…")
        self._save_btn.clicked.connect(self._save_overlay)
        self._save_btn.hide()
        self._save_row.addWidget(self._save_btn)
        layout.addLayout(self._save_row)

        # History navigation
        hist_row = QHBoxLayout()
        self._prev_btn = QPushButton("◀ Previous")
        self._prev_btn.clicked.connect(self._show_prev)
        self._next_btn = QPushButton("Next ▶")
        self._next_btn.clicked.connect(self._show_next)
        self._hist_label = QLabel("")
        self._hist_label.setStyleSheet("color: #888; font-size: 11px;")
        hist_row.addWidget(self._prev_btn)
        hist_row.addWidget(self._hist_label)
        hist_row.addStretch()
        hist_row.addWidget(self._next_btn)
        layout.addLayout(hist_row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def current_mode(self) -> str:
        return self._mode_combo.currentData()

    def show_loading(self) -> None:
        self._loading_label.show()
        self._stack.hide()
        self.show()
        self.raise_()

    def show_feedback(self, response: FeedbackResponse, overlay_image=None) -> None:
        idx = len(self._history)
        self._history.append(response)
        self._history_idx = idx
        if overlay_image is not None:
            self._overlay_images[idx] = overlay_image
        self._loading_label.hide()
        self._stack.show()
        self._render_current()
        self.show()
        self.raise_()

    def show_error(self, message: str) -> None:
        self._loading_label.hide()
        self._stack.show()
        self._stack.setCurrentIndex(0)
        self._text_edit.setMarkdown(f"**Error:** {message}")
        self._save_btn.hide()
        self.show()
        self.raise_()

    # ------------------------------------------------------------------
    # History navigation
    # ------------------------------------------------------------------

    def _show_prev(self) -> None:
        if self._history_idx > 0:
            self._history_idx -= 1
            self._render_current()

    def _show_next(self) -> None:
        if self._history_idx < len(self._history) - 1:
            self._history_idx += 1
            self._render_current()

    def _render_current(self) -> None:
        if not self._history or self._history_idx < 0:
            return
        resp = self._history[self._history_idx]
        ts = resp.timestamp.strftime("%H:%M:%S")
        mode_label = MODE_LABELS.get(resp.mode, resp.mode)
        total = len(self._history)
        idx = self._history_idx + 1
        self._hist_label.setText(f"{idx}/{total}  {ts}  [{mode_label}]")
        self._prev_btn.setEnabled(self._history_idx > 0)
        self._next_btn.setEnabled(self._history_idx < total - 1)

        overlay_img = self._overlay_images.get(self._history_idx)
        if overlay_img is not None:
            pixmap = _pil_to_pixmap(overlay_img)
            self._image_label.setPixmap(
                pixmap.scaled(
                    self._stack.width() - 8, self._stack.height() - 8,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self._stack.setCurrentIndex(1)
            self._save_btn.show()
            if resp.text:
                self._overlay_notice.setText(resp.text[:120] + ("…" if len(resp.text) > 120 else ""))
            else:
                self._overlay_notice.setText("")
        else:
            self._stack.setCurrentIndex(0)
            self._text_edit.setMarkdown(resp.text)
            self._save_btn.hide()
            self._overlay_notice.setText("")

    def _save_overlay(self) -> None:
        overlay_img = self._overlay_images.get(self._history_idx)
        if overlay_img is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Overlay Image", "drawing-coach-overlay.png", "PNG (*.png)"
        )
        if path:
            overlay_img.save(path, format="PNG")

    # ------------------------------------------------------------------
    # Dragging
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        super().keyPressEvent(event)
