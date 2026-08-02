from __future__ import annotations

from PIL import Image as PilImage
from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QImage, QKeyEvent, QMouseEvent, QPixmap, QWheelEvent
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from drawing_coach.feedback_engine import FeedbackResponse

MODE_LABELS = {
    "quick_hint": "Quick Hint",
    "full_critique": "Full Critique",
    "practice_exercise": "Practice Exercise",
    "overlay": "Overlay",
}

MIN_ZOOM = 0.25
MAX_ZOOM = 4.0
ZOOM_STEP = 1.25


def _pil_to_pixmap(img: PilImage.Image) -> QPixmap:

    rgb = img.convert("RGB")
    data = rgb.tobytes("raw", "RGB")
    qimg = QImage(
        data, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888
    )
    return QPixmap.fromImage(qimg)


class _ZoomScrollArea(QScrollArea):
    """QScrollArea that treats Ctrl+Wheel as a zoom gesture instead of scrolling."""

    def __init__(self, on_zoom_in, on_zoom_out, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_zoom_in = on_zoom_in
        self._on_zoom_out = on_zoom_out

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self._on_zoom_in()
            else:
                self._on_zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)


class FeedbackPanel(QWidget):
    """Floating, draggable panel that shows LLM feedback."""

    feedback_requested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("Feedback Management")
        self.setMinimumSize(380, 300)
        self.resize(720, 560)
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
        self._overlay_images: dict[int, PilImage.Image] = {}
        self._zoom_factor: float = 1.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Title bar
        title_row = QHBoxLayout()
        title_label = QLabel("Feedback Management")
        title_label.setStyleSheet("font-weight: bold;")
        title_row.addWidget(title_label)
        title_row.addStretch()
        dismiss_btn = QPushButton("✕")
        dismiss_btn.setFixedSize(24, 24)
        dismiss_btn.clicked.connect(self.hide)
        title_row.addWidget(dismiss_btn)
        layout.addLayout(title_row)

        # Mode selector + request trigger
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self._mode_group = QButtonGroup(self)
        for i, (key, label) in enumerate(MODE_LABELS.items()):
            radio = QRadioButton(label)
            radio.setProperty("mode_key", key)
            if i == 0:
                radio.setChecked(True)
            self._mode_group.addButton(radio)
            mode_row.addWidget(radio)
        mode_row.addStretch()
        self._request_btn = QPushButton("Request Feedback")
        self._request_btn.clicked.connect(
            lambda: self.feedback_requested.emit(self.current_mode())
        )
        mode_row.addWidget(self._request_btn)
        layout.addLayout(mode_row)

        # Loading indicator
        self._loading_label = QLabel("Thinking…")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.hide()
        layout.addWidget(self._loading_label)

        # Overlay (top) / feedback text (bottom) split
        self._splitter = QSplitter(Qt.Orientation.Vertical)

        zoom_row = QHBoxLayout()
        zoom_out_btn = QPushButton("−")
        zoom_out_btn.setFixedWidth(28)
        zoom_out_btn.clicked.connect(self._zoom_out)
        zoom_row.addWidget(zoom_out_btn)
        zoom_reset_btn = QPushButton("Reset")
        zoom_reset_btn.clicked.connect(self._zoom_reset)
        zoom_row.addWidget(zoom_reset_btn)
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedWidth(28)
        zoom_in_btn.clicked.connect(self._zoom_in)
        zoom_row.addWidget(zoom_in_btn)
        self._zoom_label = QLabel("100%")
        self._zoom_label.setStyleSheet("color: #aaa; font-size: 11px;")
        zoom_row.addWidget(self._zoom_label)
        zoom_row.addStretch()

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setScaledContents(False)
        self._image_scroll = _ZoomScrollArea(self._zoom_in, self._zoom_out)
        self._image_scroll.setWidgetResizable(True)
        self._image_scroll.setWidget(self._image_label)

        self._image_pane = QWidget()
        image_pane_layout = QVBoxLayout(self._image_pane)
        image_pane_layout.setContentsMargins(0, 0, 0, 0)
        image_pane_layout.addLayout(zoom_row)
        image_pane_layout.addWidget(self._image_scroll)
        self._splitter.addWidget(self._image_pane)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._splitter.addWidget(self._text_edit)

        layout.addWidget(self._splitter, 1)

        # Overlay save row
        self._save_row = QHBoxLayout()
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
        checked = self._mode_group.checkedButton()
        return checked.property("mode_key") if checked else None

    def show_loading(self) -> None:
        self._loading_label.show()
        self._splitter.hide()
        self.show()
        self.raise_()

    def show_feedback(
        self, response: FeedbackResponse, overlay_image: PilImage.Image | None = None
    ) -> None:
        idx = len(self._history)
        self._history.append(response)
        self._history_idx = idx
        if overlay_image is not None:
            self._overlay_images[idx] = overlay_image
        self._loading_label.hide()
        self._splitter.show()
        self._render_current()
        self.show()
        self.raise_()

    def show_error(self, message: str) -> None:
        self._loading_label.hide()
        self._splitter.show()
        self._image_pane.hide()
        self._save_btn.hide()
        self._text_edit.setMarkdown(f"**Error:** {message}")
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

        self._text_edit.setMarkdown(resp.text)
        self._set_zoom(1.0)

        overlay_img = self._overlay_images.get(self._history_idx)
        if overlay_img is not None:
            self._image_pane.show()
            self._render_overlay_image()
            self._save_btn.show()
            self._splitter.setSizes([3, 2])
        else:
            self._image_pane.hide()
            self._save_btn.hide()

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
    # Zoom
    # ------------------------------------------------------------------

    def _zoom_in(self) -> None:
        self._set_zoom(self._zoom_factor * ZOOM_STEP)

    def _zoom_out(self) -> None:
        self._set_zoom(self._zoom_factor / ZOOM_STEP)

    def _zoom_reset(self) -> None:
        self._set_zoom(1.0)

    def _set_zoom(self, factor: float) -> None:
        self._zoom_factor = max(MIN_ZOOM, min(MAX_ZOOM, factor))
        self._zoom_label.setText(f"{round(self._zoom_factor * 100)}%")
        self._render_overlay_image()

    def _render_overlay_image(self) -> None:
        overlay_img = self._overlay_images.get(self._history_idx)
        if overlay_img is None:
            return
        pixmap = _pil_to_pixmap(overlay_img)
        target_w = max(1, round(pixmap.width() * self._zoom_factor))
        target_h = max(1, round(pixmap.height() * self._zoom_factor))
        self._image_label.setPixmap(
            pixmap.scaled(
                target_w,
                target_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    # ------------------------------------------------------------------
    # Dragging
    # ------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_pos = None

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        super().keyPressEvent(event)
