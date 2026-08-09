from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QEvent, QSize, Qt, QUrl
from PyQt6.QtGui import (
    QColor,
    QDesktopServices,
    QImage,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
)
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

from drawing_coach import perf
from drawing_coach.capture_engine import CapturedFrame, CaptureEngine
from drawing_coach.design_system import IconButton
from drawing_coach.llm_config import LLMConfig
from drawing_coach.theme import Theme


def _pil_to_pixmap(frame: CapturedFrame, max_size: int = 48) -> QPixmap:
    with perf.probe(
        "history.pil_to_pixmap",
        child=True,
        px=f"{frame.image.width}x{frame.image.height}",
    ):
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
        with perf.probe("history.row_widget", child=True):
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

            self._ts_label = QLabel(frame.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
            layout.addWidget(self._ts_label, 1)

            self.delete_button = IconButton("×", size=24)
            self.delete_button.setVisible(False)
            self.delete_button.clicked.connect(lambda: self._on_delete(self._frame))
            layout.addWidget(self.delete_button)

            self._is_hovered = False
            self._is_lookback = False

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._on_open(self._frame)
        super().mouseDoubleClickEvent(event)

    def set_hovered(self, hovered: bool) -> None:
        self.delete_button.setVisible(hovered)
        self._is_hovered = hovered
        # Only the label's text color goes through setStyleSheet() (a cheap,
        # palette-based property) — the row background is painted directly
        # in paintEvent() below rather than via a stylesheet background/
        # border rule, which would need Qt::WA_StyledBackground and force a
        # full CSS re-resolution of every row (not just the hovered one) on
        # every repaint, visibly slowing down the whole list.
        if hovered:
            text_color = self.palette().color(QPalette.ColorRole.HighlightedText).name()
            self._ts_label.setStyleSheet(f"color: {text_color};")  # theme-exempt
        else:
            self._ts_label.setStyleSheet("")  # theme-exempt
        self.update()

    def set_highlighted(self, highlighted: bool) -> None:
        self._is_lookback = highlighted
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        # Guarded at the callsite: this runs per row per repaint, so when
        # instrumentation is off it must not even construct a probe.
        if not perf.ON:
            self._paint(event)
            return
        with perf.probe("history.row_paint", child=True):
            self._paint(event)

    def _paint(self, event) -> None:
        painter = QPainter(self)
        if self._is_hovered:
            # Runtime QPalette-driven hover color, must follow the OS's
            # active theme (see design.md Non-Goals).
            painter.fillRect(
                self.rect(), self.palette().color(QPalette.ColorRole.Highlight)
            )  # theme-exempt
        if self._is_lookback:
            pen = QPen(QColor(Theme.dialog.lookback_border))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.drawLine(1, 0, 1, self.height())
        super().paintEvent(event)


class HistoryPanel(QDialog):
    def __init__(
        self,
        engine: CaptureEngine,
        config: LLMConfig,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        perf.track(self)
        self._engine = engine
        self._config = config
        self.setWindowTitle("Session History")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        self._info_label = QLabel()
        layout.addWidget(self._info_label)

        self._list_widget = QListWidget()
        self._list_widget.setIconSize(QSize(48, 48))
        # Row hover is driven by the viewport's own mouse-move tracking rather
        # than Enter/Leave events on the embedded row widget — Enter/Leave
        # delivery to a setItemWidget() child is unreliable on macOS (the
        # viewport intercepts hover crossings for hit-testing first).
        self._list_widget.setMouseTracking(True)
        self._list_widget.viewport().setMouseTracking(True)
        self._list_widget.viewport().installEventFilter(self)
        self._hovered_row: _FrameRowWidget | None = None
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

    def eventFilter(self, obj, event):  # noqa: N802 - Qt override
        if obj is self._list_widget.viewport():
            if event.type() == QEvent.Type.MouseMove:
                # Guarded at the callsite: fires on every mouse-move.
                if perf.ON:
                    with perf.probe("history.hover_hit_test", child=True):
                        self._hover_at(event.pos())
                else:
                    self._hover_at(event.pos())
            elif event.type() == QEvent.Type.Leave:
                self._set_hovered_row(None)
        return super().eventFilter(obj, event)

    def _hover_at(self, pos) -> None:
        item = self._list_widget.itemAt(pos)
        widget = self._list_widget.itemWidget(item) if item is not None else None
        self._set_hovered_row(widget if isinstance(widget, _FrameRowWidget) else None)

    def _set_hovered_row(self, widget: _FrameRowWidget | None) -> None:
        if widget is self._hovered_row:
            return
        if self._hovered_row is not None:
            self._hovered_row.set_hovered(False)
        self._hovered_row = widget
        if widget is not None:
            widget.set_hovered(True)

    def _render(self) -> None:
        with perf.probe("history.render") as p:
            self._hovered_row = None
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

            # Panel/receiver counts ride along on every render so the log states
            # how many closed-but-still-subscribed panels are doing this work.
            p.set(
                frames=len(frames),
                rows=self._list_widget.count(),
                panels=perf.instance_count("HistoryPanel"),
                receivers=perf.signal_receivers(
                    self._engine, self._engine.frames_changed
                ),
            )

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
        with perf.probe("history.lookback", child=True):
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
