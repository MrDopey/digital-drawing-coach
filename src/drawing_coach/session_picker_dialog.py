from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from drawing_coach.editable_name_label import EditableNameLabel
from drawing_coach.session_manager import (
    SessionInfo,
    default_session_name,
    delete_session,
    list_sessions,
    write_session_name,
)

THUMB_SIZE = QSize(120, 80)
PREVIEW_SIZE = QSize(360, 240)


class _ThumbnailLabel(QLabel):
    """Session thumbnail; double-click resumes, hover previews at full size."""

    doubleClicked = pyqtSignal()

    def __init__(self, thumbnail: Path | None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(THUMB_SIZE)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = QPixmap(str(thumbnail)) if thumbnail and thumbnail.exists() else None
        if pix and not pix.isNull():
            self.setPixmap(
                pix.scaled(
                    THUMB_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.setToolTip(
                f'<img src="{thumbnail.as_uri()}" '
                f'width="{PREVIEW_SIZE.width()}" height="{PREVIEW_SIZE.height()}">'
            )
        else:
            self.setStyleSheet("background: #cccccc;")

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)


class _SessionRow(QFrame):
    """One row in the picker: thumbnail, editable name, date, pencil button."""

    clicked = pyqtSignal()
    resume_requested = pyqtSignal()
    renamed = pyqtSignal()

    def __init__(self, info: SessionInfo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.info = info
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.set_selected(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self._thumb = _ThumbnailLabel(info.thumbnail)
        self._thumb.doubleClicked.connect(self.resume_requested)
        layout.addWidget(self._thumb)

        text_col = QVBoxLayout()
        self._name_label = EditableNameLabel(info.name)
        self._name_label.renamed.connect(self._on_renamed)
        text_col.addWidget(self._name_label)

        date_label = QLabel(info.start_time.strftime("%Y-%m-%d %H:%M"))
        date_label.setStyleSheet("color: #888;")
        date_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        text_col.addWidget(date_label)
        layout.addLayout(text_col, 1)

        pencil_btn = QToolButton()
        pencil_btn.setText("✎")
        pencil_btn.setToolTip("Rename session")
        pencil_btn.clicked.connect(self._name_label.start_edit)
        layout.addWidget(pencil_btn)

    def set_selected(self, selected: bool) -> None:
        color = "#3b82f6" if selected else "#d1d5db"
        self.setStyleSheet(
            f"_SessionRow {{ border: 2px solid {color}; border-radius: 4px; }}"
        )

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self.clicked.emit()
        super().mousePressEvent(event)

    def _on_renamed(self, text: str) -> None:
        if text:
            write_session_name(self.info.path, text)
            self.info.name = text
        else:
            default = default_session_name(self.info.start_time, self.info.drawing_app)
            write_session_name(self.info.path, "")
            self.info.name = default
            self._name_label.set_name(default)
        self.renamed.emit()


class SessionPickerDialog(QDialog):
    """Launch-time picker: Resume / New Session / Delete a saved session."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select a Session")
        self.setMinimumSize(560, 420)
        self.result_action: str = "quit"
        self.result_session: Path | None = None
        self._selected_row: _SessionRow | None = None
        self._rows: list[_SessionRow] = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Resume a previous session or start a new one:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        self._rows_layout = QVBoxLayout(container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        for info in list_sessions():
            self._add_row(info)

        btn_row = QHBoxLayout()
        new_btn = QPushButton("New Session")
        new_btn.clicked.connect(self._new)
        btn_row.addWidget(new_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._delete)
        btn_row.addWidget(self._delete_btn)

        btn_row.addStretch()

        self._resume_btn = QPushButton("Resume")
        self._resume_btn.setDefault(True)
        self._resume_btn.setEnabled(False)
        self._resume_btn.clicked.connect(lambda: self._resume())
        btn_row.addWidget(self._resume_btn)
        layout.addLayout(btn_row)

        if self._rows:
            self._select(self._rows[0])

    def _add_row(self, info: SessionInfo) -> None:
        row = _SessionRow(info)
        row.clicked.connect(lambda r=row: self._select(r))
        row.resume_requested.connect(lambda r=row: self._resume(r))
        self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)
        self._rows.append(row)

    def _select(self, row: _SessionRow) -> None:
        if self._selected_row is not None:
            self._selected_row.set_selected(False)
        self._selected_row = row
        row.set_selected(True)
        self._resume_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)

    def _resume(self, row: "_SessionRow | None" = None) -> None:
        row = row or self._selected_row
        if row is None:
            return
        self.result_action = "resume"
        self.result_session = row.info.path
        self.accept()

    def _new(self) -> None:
        self.result_action = "new"
        self.result_session = None
        self.accept()

    def _delete(self) -> None:
        row = self._selected_row
        if row is None:
            return
        confirm = QMessageBox.question(
            self,
            "Delete Session",
            f"Delete session '{row.info.name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        delete_session(row.info.path)
        self._rows.remove(row)
        self._selected_row = None
        self._resume_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)
        row.setParent(None)
        row.deleteLater()
        if self._rows:
            self._select(self._rows[0])

    def reject(self) -> None:  # type: ignore[override]
        self.result_action = "quit"
        self.result_session = None
        super().reject()

    @staticmethod
    def choose_session(parent: QWidget | None = None) -> tuple[str, Path | None]:
        """Show the picker, or skip it and return ('new', None) if no sessions exist."""
        if not list_sessions():
            return ("new", None)
        dlg = SessionPickerDialog(parent)
        dlg.exec()
        return dlg.result_action, dlg.result_session
