from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from drawing_coach.capture_engine import CapturedFrame


def _pil_to_pixmap(frame: CapturedFrame, max_size: int = 120) -> QPixmap:
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
            list_widget.setViewMode(QListWidget.ViewMode.IconMode)
            list_widget.setIconSize(QSize(120, 120))
            list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
            list_widget.setSpacing(8)

            for frame in frames:
                ts = frame.timestamp.strftime("%H:%M:%S")
                item = QListWidgetItem(ts)
                item.setIcon(
                    QIcon(_pil_to_pixmap(frame).scaled(
                        120,
                        120,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    ))
                )
                item.setSizeHint(QSize(140, 150))
                list_widget.addItem(item)

            layout.addWidget(list_widget)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(close_btn)
        layout.addLayout(row)
