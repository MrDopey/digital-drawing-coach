"""Reusable styled widgets sourcing all colors/spacing from `theme.py`.

Callers compose these instead of writing their own `setStyleSheet()` calls,
so a token change in `theme.py` propagates to every call site automatically.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QWidget

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


class PillBadge(QLabel):
    """A label whose text color reflects a semantic status. Covers both the
    success/danger/warning check-result pattern (diagnostics, settings) and
    one-off status colors that don't fit the three named variants (`color=`)."""

    _VARIANTS = {
        "success": Theme.success,
        "danger": Theme.danger,
        "warning": Theme.warning,
        "neutral": "",
    }

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        *,
        variant: str = "neutral",
        color: str | None = None,
    ) -> None:
        super().__init__(text, parent)
        if color is not None:
            self.set_color(color)
        else:
            self.set_variant(variant)

    def set_variant(self, variant: str) -> None:
        self.set_color(self._VARIANTS.get(variant, ""))

    def set_color(self, color: str | None) -> None:
        self.setStyleSheet(f"color: {color};" if color else "")


class MutedLabel(QLabel):
    """Secondary/muted text label. `dim=True` selects the overlay's slightly
    lighter muted variant; `small=True` adds the app's small font size;
    `extra_style` appends any additional QSS a specific call site needs."""

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        *,
        dim: bool = False,
        small: bool = False,
        extra_style: str = "",
    ) -> None:
        super().__init__(text, parent)
        color = Theme.overlay.muted_text_dim if dim else Theme.muted_text
        style = f"color: {color};"
        if small:
            style += f" font-size: {Theme.font_size_small};"
        if extra_style:
            style += " " + extra_style
        self.setStyleSheet(style)


class SectionHeader(QLabel):
    """A bold section/title label."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet("font-weight: bold;")


class PrimaryButton(QPushButton):
    """The feedback panel's standard button styling (dark overlay surface)."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setStyleSheet(
            f"PrimaryButton {{ background: {Theme.overlay.button_background};"
            f" border-radius: {Theme.border_radius}; padding: {Theme.button_padding}; }}"
            f"PrimaryButton:hover {{ background: {Theme.overlay.button_hover}; }}"
        )


class IconButton(QPushButton):
    """A small fixed-size icon-only button (e.g. a row's hover-reveal delete
    control) — no padding, unlike `PrimaryButton`, so a glyph isn't clipped."""

    def __init__(
        self, text: str = "", parent: QWidget | None = None, *, size: int = 24
    ) -> None:
        super().__init__(text, parent)
        self.setFixedSize(size, size)
        self.setStyleSheet(
            f"IconButton {{ background: {Theme.overlay.button_background};"
            f" color: {Theme.overlay.text}; border-radius: {Theme.border_radius}; }}"
            f"IconButton:hover {{ background: {Theme.overlay.button_hover}; }}"
        )
