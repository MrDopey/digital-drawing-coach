from __future__ import annotations

import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from drawing_coach.memory_store import MemoryStore
from drawing_coach.paths import memory_path, memory_summaries_path


class MemoryViewerDialog(QDialog):
    def __init__(
        self, memory_store: MemoryStore, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Memory Viewer")
        self.setMinimumSize(520, 480)
        self._store = memory_store

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Current coach's notes:"))
        self._notes_view = QTextEdit()
        self._notes_view.setReadOnly(True)
        self._notes_view.setMaximumHeight(120)
        layout.addWidget(self._notes_view)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Category / Date", "Note", ""])
        self._tree.setColumnWidth(0, 160)
        layout.addWidget(self._tree, 1)

        btn_row = QHBoxLayout()
        clear_btn = QPushButton("Clear All Memory")
        clear_btn.clicked.connect(self._clear_all)
        btn_row.addWidget(clear_btn)
        export_btn = QPushButton("Export Memory…")
        export_btn.clicked.connect(self._export)
        btn_row.addWidget(export_btn)
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._refresh()

    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        self._notes_view.setPlainText(
            self._store.summarise() or "No coach's notes yet."
        )
        self._tree.clear()

        observations = self._store.observations()
        if not observations:
            self._tree.addTopLevelItem(
                QTreeWidgetItem(["No observations recorded yet", "", ""])
            )
            return

        by_category: dict[str, list[int]] = {}
        for idx, obs in enumerate(observations):
            by_category.setdefault(obs.category, []).append(idx)

        for category in sorted(by_category, key=lambda c: -len(by_category[c])):
            indices = sorted(
                by_category[category], key=lambda i: observations[i].date, reverse=True
            )
            cat_item = QTreeWidgetItem([f"{category} ({len(indices)})", "", ""])
            self._tree.addTopLevelItem(cat_item)
            for idx in indices:
                obs = observations[idx]
                child = QTreeWidgetItem([obs.date, obs.note, ""])
                cat_item.addChild(child)
                delete_btn = QPushButton("Delete")
                delete_btn.clicked.connect(lambda _, i=idx: self._delete(i))
                self._tree.setItemWidget(child, 2, delete_btn)

        self._tree.expandAll()

    def _delete(self, idx: int) -> None:
        self._store.delete(idx)
        self._refresh()

    def _clear_all(self) -> None:
        reply = QMessageBox.question(
            self,
            "Clear All Memory",
            "This will permanently delete all stored observations and the"
            " summary history. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._store.clear()
            self._refresh()

    def _export(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Export Memory To")
        if not directory:
            return
        dest = Path(directory)
        exported = []
        for src in (memory_path(), memory_summaries_path()):
            if src.exists():
                shutil.copy2(src, dest / src.name)
                exported.append(src.name)
        if exported:
            QMessageBox.information(
                self, "Exported", f"Exported: {', '.join(exported)}"
            )
        else:
            QMessageBox.information(
                self, "Nothing to Export", "No memory files exist yet."
            )
