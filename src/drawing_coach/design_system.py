"""Reusable styled widgets sourcing all colors/spacing from `theme.py`.

Callers compose these instead of writing their own `setStyleSheet()` calls,
so a token change in `theme.py` propagates to every call site automatically.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QWidget

from drawing_coach.theme import Theme


class Card(QFrame):
    """Bordered/filled container. Covers both existing patterns: a filled
    callout (background + border, e.g. a popup) and a border-only selectable
    row whose border color toggles (e.g. a selection indicator)."""

    def __init__(
        self,
        parent: QWidget | None = None,
        flags: Qt.WindowType | None = None,
        *,
        background: str | None = None,
        border: str | None = None,
        border_width: str = Theme.border_width_thin,
        radius: str | None = None,
    ) -> None:
        if flags is not None:
            super().__init__(parent, flags)
        else:
            super().__init__(parent)
        self._background = background
        self._border_width = border_width
        self._radius = radius
        self._border = border
        self._apply_style()

    def set_border(self, color: str | None) -> None:
        self._border = color
        self._apply_style()

    def _apply_style(self) -> None:
        rules = []
        if self._background:
            rules.append(f"background: {self._background};")
        if self._border:
            rules.append(f"border: {self._border_width} solid {self._border};")
        if self._radius:
            rules.append(f"border-radius: {self._radius};")
        self.setStyleSheet(f"{type(self).__name__} {{ {' '.join(rules)} }}")
