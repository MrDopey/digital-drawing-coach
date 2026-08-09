from __future__ import annotations

from PyQt6.QtCore import Qt
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
from drawing_coach.window_manager import WindowInfo, WindowManager


class AppSelectionDialog(QDialog):
    def __init__(self, manager: WindowManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        perf.track(self)
        self.setWindowTitle("Select Drawing Application")
        self.setMinimumSize(480, 400)
        self._manager = manager
        self.selected_window: WindowInfo | None = None

        layout = QVBoxLayout(self)

        self._status_label = QLabel("Select the window you are drawing in:")
        layout.addWidget(self._status_label)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._confirm)
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._populate)
        btn_row.addWidget(refresh_btn)
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        self._confirm_btn = QPushButton("Select")
        self._confirm_btn.setDefault(True)
        self._confirm_btn.clicked.connect(self._confirm)
        btn_row.addWidget(self._confirm_btn)
        layout.addLayout(btn_row)

        self._populate()

    def _populate(self) -> None:
        self._list.clear()
        windows = self._manager.list_windows()
        if not windows:
            self._status_label.setText(
                "No windows found — open your drawing application and click Refresh."
            )
            return
        self._status_label.setText("Select the window you are drawing in:")
        for win in windows:
            item = QListWidgetItem(
                f"{win.app_name}  —  {win.title}" if win.app_name else win.title
            )
            item.setData(Qt.ItemDataRole.UserRole, win)
            self._list.addItem(item)

    def _confirm(self) -> None:
        item = self._list.currentItem()
        if item is None:
            QMessageBox.information(
                self, "No selection", "Please select a window first."
            )
            return
        self.selected_window = item.data(Qt.ItemDataRole.UserRole)
        self.accept()
