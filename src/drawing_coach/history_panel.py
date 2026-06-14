from __future__ import annotations

import os
import tempfile
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon, QImage, QPixmap
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

from drawing_coach.capture_engine import CapturedFrame


def _pil_to_pixmap(frame: CapturedFrame, max_size: int = 48) -> QPixmap:
    img = frame.image.copy()
    img.thumbnail((max_size, max_size))
    data = img.convert("RGB").tobytes("raw", "RGB")
    qimg = QImage(
        data, img.width, img.height, img.width * 3, QImage.Format.Format_RGB888
    )
    return QPixmap.fromImage(qimg)


class HistoryPanel(QDialog):
    def __init__(
        self, frames: list[CapturedFrame], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Session History")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        if not frames:
            layout.addWidget(QLabel("No captures yet — wait for the first screenshot."))
        else:
            label = QLabel(f"{len(frames)} frames captured this session:")
            layout.addWidget(label)

            list_widget = QListWidget()
            list_widget.setIconSize(QSize(48, 48))

            for frame in reversed(frames):
                ts = frame.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                item = QListWidgetItem(ts)
                item.setIcon(
                    QIcon(_pil_to_pixmap(frame).scaled(
                        48,
                        48,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ))
                )
                item.setData(Qt.ItemDataRole.UserRole, frame)
                list_widget.addItem(item)

            list_widget.itemDoubleClicked.connect(self._open_frame)
            layout.addWidget(list_widget)

            hint = QLabel("Double-click a thumbnail to open it in the default viewer.")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(hint)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close_btn)
        layout.addLayout(row)

    def _open_frame(self, item: QListWidgetItem) -> None:
        frame: CapturedFrame = item.data(Qt.ItemDataRole.UserRole)

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
