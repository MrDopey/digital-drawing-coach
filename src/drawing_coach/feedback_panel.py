from __future__ import annotations

from pathlib import Path

from PIL import Image as PilImage
from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import (
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPixmap,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from drawing_coach.capture_engine import CapturedFrame
from drawing_coach.design_system import MutedLabel, PrimaryButton, SectionHeader
from drawing_coach.feedback_engine import FeedbackResponse
from drawing_coach.feedback_store import FeedbackStore
from drawing_coach.theme import Theme

MODE_LABELS = {
    "quick_hint": "Quick Hint",
    "full_critique": "Full Critique",
    "practice_exercise": "Practice Exercise",
    "overlay": "Overlay",
}

_CATEGORY_LABELS = {
    "anatomy": "Anatomy",
    "gesture": "Gesture",
    "line_quality": "Line Quality",
    "composition": "Composition",
    "progress": "Progress",
}


def _category_label(category: str) -> str:
    return _CATEGORY_LABELS.get(category, category.replace("_", " ").strip().title())


def _format_observations_markdown(observations: list[dict]) -> str:
    """Render the LLM's structured `observations` as a markdown section.

    These often carry the concrete, actionable detail that `feedback_text`
    only summarises in passing, so they need to be shown alongside it.
    """
    by_category: dict[str, list[str]] = {}
    for obs in observations:
        note = obs.get("note", "").strip()
        if not note:
            continue
        by_category.setdefault(obs.get("category", ""), []).append(note)
    if not by_category:
        return ""

    lines = ["### Detailed Observations"]
    for category in sorted(by_category):
        lines.append(f"\n**{_category_label(category)}**")
        lines.extend(f"- {note}" for note in by_category[category])
    return "\n".join(lines)

MIN_ZOOM = 0.25
MAX_ZOOM = 4.0
ZOOM_STEP = 1.25

SIDEBAR_WIDTH = 180


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
    mode_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("Feedback Management")
        self.setMinimumSize(380, 300)
        self.resize(720, 560)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        Theme.overlay.apply_to(self)

        self._drag_pos: QPoint | None = None
        self._history: list[FeedbackResponse] = []
        self._history_idx: int = -1
        self._overlay_images: dict[int, PilImage.Image] = {}
        self._frame_paths: dict[int, Path] = {}
        # Source pixmap for the entry on screen, converted once per entry so
        # zooming re-scales rather than re-decoding a full-resolution frame.
        self._current_pixmap: QPixmap | None = None
        self._zoom_factor: float = 1.0
        self._store: FeedbackStore | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Title bar
        title_row = QHBoxLayout()
        title_label = SectionHeader("Feedback Management")
        title_row.addWidget(title_label)
        title_row.addStretch()
        dismiss_btn = PrimaryButton("✕")
        dismiss_btn.setFixedSize(24, 24)
        dismiss_btn.clicked.connect(self.hide)
        title_row.addWidget(dismiss_btn)
        layout.addLayout(title_row)

        # Left sidebar: reverse-chronological history list
        self._sidebar = QListWidget()
        self._sidebar.setFixedWidth(SIDEBAR_WIDTH)
        self._sidebar.currentRowChanged.connect(self._on_sidebar_row_changed)

        # Right-hand container: everything the panel already had, unchanged
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)

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
        self._mode_group.buttonToggled.connect(self._on_mode_toggled)
        mode_row.addStretch()
        self._request_btn = PrimaryButton("Request Feedback")
        self._request_btn.clicked.connect(
            lambda: self.feedback_requested.emit(self.current_mode())
        )
        mode_row.addWidget(self._request_btn)
        right_layout.addLayout(mode_row)

        # Loading indicator
        self._loading_label = QLabel("Thinking…")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.hide()
        right_layout.addWidget(self._loading_label)

        # Overlay (top) / feedback text (bottom) split
        self._splitter = QSplitter(Qt.Orientation.Vertical)

        zoom_row = QHBoxLayout()
        zoom_out_btn = PrimaryButton("−")
        zoom_out_btn.setFixedWidth(28)
        zoom_out_btn.clicked.connect(self._zoom_out)
        zoom_row.addWidget(zoom_out_btn)
        zoom_reset_btn = PrimaryButton("Reset")
        zoom_reset_btn.clicked.connect(self._zoom_reset)
        zoom_row.addWidget(zoom_reset_btn)
        zoom_in_btn = PrimaryButton("+")
        zoom_in_btn.setFixedWidth(28)
        zoom_in_btn.clicked.connect(self._zoom_in)
        zoom_row.addWidget(zoom_in_btn)
        self._zoom_label = MutedLabel("100%", dim=True, small=True)
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

        right_layout.addWidget(self._splitter, 1)

        # Overlay save row
        self._save_row = QHBoxLayout()
        self._save_row.addStretch()
        self._save_btn = PrimaryButton("Save Overlay…")
        self._save_btn.clicked.connect(self._save_overlay)
        self._save_btn.hide()
        self._save_row.addWidget(self._save_btn)
        right_layout.addLayout(self._save_row)

        # History navigation
        hist_row = QHBoxLayout()
        self._prev_btn = PrimaryButton("◀ Previous")
        self._prev_btn.clicked.connect(self._show_prev)
        self._next_btn = PrimaryButton("Next ▶")
        self._next_btn.clicked.connect(self._show_next)
        self._hist_label = MutedLabel("", small=True)
        hist_row.addWidget(self._prev_btn)
        hist_row.addWidget(self._hist_label)
        hist_row.addStretch()
        hist_row.addWidget(self._next_btn)
        right_layout.addLayout(hist_row)

        self._outer_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._outer_splitter.addWidget(self._sidebar)
        self._outer_splitter.addWidget(right_container)
        layout.addWidget(self._outer_splitter, 1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def current_mode(self) -> str:
        checked = self._mode_group.checkedButton()
        return checked.property("mode_key") if checked else None

    def _on_mode_toggled(self, button: QRadioButton, checked: bool) -> None:
        if checked:
            self.mode_changed.emit(self.current_mode())

    def update_request_state(self, frame_hashes: list[str]) -> None:
        """Disable Request Feedback when frame_hashes+mode already match the
        last saved entry for that mode; re-enable it otherwise."""
        match = (
            self._store.last_entry_for(self.current_mode(), frame_hashes)
            if self._store is not None
            else None
        )
        if match is not None:
            self._request_btn.setEnabled(False)
            self._request_btn.setToolTip("Already generated for this drawing and mode")
        else:
            self._request_btn.setEnabled(True)
            self._request_btn.setToolTip("")

    def show_loading(self) -> None:
        self._loading_label.show()
        self._splitter.hide()
        self.show()
        self.raise_()

    def show_feedback(
        self,
        response: FeedbackResponse,
        overlay_image: PilImage.Image | None = None,
        last_frame: CapturedFrame | None = None,
    ) -> None:
        idx = len(self._history)
        self._history.append(response)
        self._history_idx = idx
        if overlay_image is not None:
            self._overlay_images[idx] = overlay_image
        if self._store is not None:
            self._store.save(response, last_frame, overlay_image)
            frame_path = self._store.frame_path_for(response)
            if frame_path is not None:
                self._frame_paths[idx] = frame_path
        self._sidebar.blockSignals(True)
        self._sidebar.insertItem(0, QListWidgetItem(self._sidebar_label(response)))
        self._sidebar.setCurrentRow(0)
        self._sidebar.blockSignals(False)
        self._loading_label.hide()
        self._splitter.show()
        self._render_current()
        self.show()
        self.raise_()

    def show_error(self, message: str) -> None:
        self._loading_label.hide()
        self._splitter.show()
        self._current_pixmap = None
        self._image_pane.hide()
        self._save_btn.hide()
        self._text_edit.setMarkdown(f"**Error:** {message}")
        self.show()
        self.raise_()

    def set_store(self, store: FeedbackStore) -> None:
        """(Re)bind the panel to `store`, replacing any previously-loaded history."""
        self._store = store
        self._history = store.load()
        self._overlay_images = {}
        self._frame_paths = {}
        for idx, response in enumerate(self._history):
            overlay_img = store.overlay_image_for(response)
            if overlay_img is not None:
                self._overlay_images[idx] = overlay_img
            frame_path = store.frame_path_for(response)
            if frame_path is not None:
                self._frame_paths[idx] = frame_path
        self._rebuild_sidebar()
        # Reset first: _on_sidebar_row_changed short-circuits when the new row
        # maps to the index already showing, which would leave the previous
        # session's image on screen.
        self._history_idx = -1
        if self._history:
            self._sidebar.setCurrentRow(0)
        else:
            self._clear_display()

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    @staticmethod
    def _sidebar_label(response: FeedbackResponse) -> str:
        mode_label = MODE_LABELS.get(response.mode, response.mode)
        return f"{response.timestamp.strftime('%d %b  %H:%M')}: {mode_label}"

    def _rebuild_sidebar(self) -> None:
        self._sidebar.blockSignals(True)
        self._sidebar.clear()
        for response in reversed(self._history):
            self._sidebar.addItem(QListWidgetItem(self._sidebar_label(response)))
        self._sidebar.blockSignals(False)

    def _on_sidebar_row_changed(self, row: int) -> None:
        if row < 0 or not self._history:
            return
        idx = len(self._history) - 1 - row
        if idx == self._history_idx:
            return
        self._history_idx = idx
        self._render_current()

    def _clear_display(self) -> None:
        self._hist_label.setText("")
        self._prev_btn.setEnabled(False)
        self._next_btn.setEnabled(False)
        self._text_edit.clear()
        self._current_pixmap = None
        self._image_pane.hide()
        self._save_btn.hide()

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
        sidebar_row = len(self._history) - 1 - self._history_idx
        self._sidebar.blockSignals(True)
        self._sidebar.setCurrentRow(sidebar_row)
        self._sidebar.blockSignals(False)

        resp = self._history[self._history_idx]
        ts = resp.timestamp.strftime("%H:%M:%S")
        mode_label = MODE_LABELS.get(resp.mode, resp.mode)
        total = len(self._history)
        idx = self._history_idx + 1
        self._hist_label.setText(f"{idx}/{total}  {ts}  [{mode_label}]")
        self._prev_btn.setEnabled(self._history_idx > 0)
        self._next_btn.setEnabled(self._history_idx < total - 1)

        observations_md = _format_observations_markdown(resp.observations)
        if observations_md:
            markdown = f"{resp.text.rstrip()}\n\n---\n\n{observations_md}"
        else:
            markdown = resp.text
        self._text_edit.setMarkdown(markdown)

        self._current_pixmap = self._load_source_pixmap(self._history_idx)
        self._save_btn.setVisible(self._history_idx in self._overlay_images)
        if self._current_pixmap is None:
            self._image_pane.hide()
        else:
            self._image_pane.show()
            self._splitter.setSizes([3, 2])
        # Re-renders the newly-selected image at the default zoom level.
        self._set_zoom(1.0)

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
        self._render_image()

    def _load_source_pixmap(self, idx: int) -> QPixmap | None:
        """The image for entry `idx`: its overlay if any, else its captured frame.

        Returns None when neither is available — the entry predates frame paths,
        or its frame has since been removed — and the image pane stays hidden.
        """
        overlay_img = self._overlay_images.get(idx)
        if overlay_img is not None:
            return _pil_to_pixmap(overlay_img)
        frame_path = self._frame_paths.get(idx)
        if frame_path is None:
            return None
        try:
            return _pil_to_pixmap(PilImage.open(frame_path))
        except OSError:
            return None

    def _render_image(self) -> None:
        pixmap = self._current_pixmap
        if pixmap is None:
            return
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
