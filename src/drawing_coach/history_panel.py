from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QEvent, QSize, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QImage, QPalette, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from drawing_coach.capture_engine import CapturedFrame, CaptureEngine
from drawing_coach.llm_config import LLMConfig

_LOOKBACK_BORDER = "border-left: 3px solid #4A90D9;"
_DELETE_BUTTON_STYLE = (
    "QPushButton { background: #333; color: #e0e0e0; border-radius: 4px; }"
    "QPushButton:hover { background: #444; }"
)


def _pil_to_pixmap(frame: CapturedFrame, max_size: int = 48) -> QPixmap:
    img = frame.image.copy()
    img.thumbnail((max_size, max_size))
    data = img.convert("RGB").tobytes("raw", "RGB")
    qimg = QImage(
        data, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888
    )
    return QPixmap.fromImage(qimg)


class _FrameRowWidget(QWidget):
    """A single history-panel row: thumbnail + timestamp + hover-visible delete button."""

    def __init__(
        self,
        frame: CapturedFrame,
        on_delete: Callable[[CapturedFrame], None],
        on_open: Callable[[CapturedFrame], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._frame = frame
        self._on_delete = on_delete
        self._on_open = on_open

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        thumb = QLabel()
        thumb.setPixmap(
            _pil_to_pixmap(frame).scaled(
                48,
                48,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        layout.addWidget(thumb)

        ts_label = QLabel(frame.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        layout.addWidget(ts_label, 1)

        self.delete_button = QPushButton("×")
        self.delete_button.setFixedSize(24, 24)
        self.delete_button.setVisible(False)
        self.delete_button.setStyleSheet(_DELETE_BUTTON_STYLE)
        self.delete_button.clicked.connect(lambda: self._on_delete(self._frame))
        layout.addWidget(self.delete_button)

        self._is_hovered = False
        self._is_lookback = False

        self.installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802 - Qt override
        if obj is self:
            if event.type() == QEvent.Type.Enter:
                self.delete_button.setVisible(True)
                self._is_hovered = True
                self._apply_style()
            elif event.type() == QEvent.Type.Leave:
                self.delete_button.setVisible(False)
                self._is_hovered = False
                self._apply_style()
        return super().eventFilter(obj, event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._on_open(self._frame)
        super().mouseDoubleClickEvent(event)

    def set_highlighted(self, highlighted: bool) -> None:
        self._is_lookback = highlighted
        self._apply_style()

    def _apply_style(self) -> None:
        style = ""
        if self._is_hovered:
            palette = self.palette()
            background = palette.color(QPalette.ColorRole.Highlight).name()
            text_color = palette.color(QPalette.ColorRole.HighlightedText).name()
            style += (
                f"_FrameRowWidget {{ background: {background}; }}"
                f"_FrameRowWidget QLabel {{ color: {text_color}; }}"
            )
        if self._is_lookback:
            style += _LOOKBACK_BORDER
        self.setStyleSheet(style)


class HistoryPanel(QDialog):
    def __init__(
        self,
        engine: CaptureEngine,
        config: LLMConfig,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._engine = engine
        self._config = config
        self.setWindowTitle("Session History")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        self._info_label = QLabel()
        layout.addWidget(self._info_label)

        self._list_widget = QListWidget()
        self._list_widget.setIconSize(QSize(48, 48))
        layout.addWidget(self._list_widget, 1)

        self._hint_label = QLabel(
            "Double-click a thumbnail to open it in the default viewer."
        )
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._hint_label)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close_btn)
        layout.addLayout(row)

        self._engine.frames_changed.connect(self._render)
        self._render()

    def _render(self) -> None:
        self._list_widget.clear()
        frames = self._engine.get_frames()

        has_frames = bool(frames)
        self._list_widget.setVisible(has_frames)
        self._hint_label.setVisible(has_frames)
        if not has_frames:
            self._info_label.setText(
                "No captures yet — wait for the first screenshot."
            )
        else:
            self._info_label.setText(f"{len(frames)} frames captured this session:")
            for frame in reversed(frames):
                self._add_row(frame)

        self._update_lookback_indicator()

    def _add_row(self, frame: CapturedFrame) -> None:
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, frame)
        row_widget = _FrameRowWidget(frame, self._delete_frame, self._open_frame)
        item.setSizeHint(row_widget.sizeHint())
        self._list_widget.addItem(item)
        self._list_widget.setItemWidget(item, row_widget)

    def _delete_frame(self, frame: CapturedFrame) -> None:
        self._engine.remove_frame(frame)

    def _update_lookback_indicator(self) -> None:
        frames = self._engine.get_frames()
        if not frames:
            return
        lookback = max(0, self._config.lookback_frames)
        window = frames[-(lookback + 1) :]

        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            frame: CapturedFrame = item.data(Qt.ItemDataRole.UserRole)
            widget = self._list_widget.itemWidget(item)
            if isinstance(widget, _FrameRowWidget):
                widget.set_highlighted(any(f is frame for f in window))

    def _open_frame(self, frame: CapturedFrame) -> None:
        if frame.path is not None:
            path = frame.path
        else:
            fd, tmp = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            path = Path(tmp)
            frame.image.save(path, format="PNG")

        ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        if not ok:
            QMessageBox.warning(
                self,
                "Cannot Open Image",
                "No default image viewer is registered for PNG files.",
            )
