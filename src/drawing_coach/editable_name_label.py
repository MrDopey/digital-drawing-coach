from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QLineEdit, QStackedWidget, QWidget


class EditableNameLabel(QStackedWidget):
    """A QLabel that swaps to an inline QLineEdit on double-click or `start_edit()`.

    Commits on Enter or focus-loss (both fire `QLineEdit.editingFinished`) and
    emits `renamed` with the new text, or an empty string if the user cleared
    the field — the caller decides what default to restore in that case.
    """

    renamed = pyqtSignal(str)

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._label = QLabel(name)
        self._label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self._label.installEventFilter(self)
        self._edit = QLineEdit(name)
        self._edit.editingFinished.connect(self._commit)
        self.addWidget(self._label)
        self.addWidget(self._edit)

    def name(self) -> str:
        return self._label.text()

    def set_name(self, name: str) -> None:
        self._label.setText(name)
        self._edit.setText(name)

    def start_edit(self) -> None:
        self._edit.setText(self._label.text())
        self.setCurrentWidget(self._edit)
        self._edit.setFocus()
        self._edit.selectAll()

    def eventFilter(self, obj, event) -> bool:  # type: ignore[override]
        if obj is self._label and event.type() == QEvent.Type.MouseButtonDblClick:
            self.start_edit()
            return True
        return super().eventFilter(obj, event)

    def _commit(self) -> None:
        if self.currentWidget() is not self._edit:
            return
        text = self._edit.text().strip()
        self.setCurrentWidget(self._label)
        if text:
            self._label.setText(text)
        self.renamed.emit(text)
