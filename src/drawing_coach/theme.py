"""Single source of truth for color, spacing, and font-size tokens.

Two surfaces exist by design: the frameless, always-on-top feedback panel is a
dark OSD-style overlay, while every other dialog/window stays on the system's
native (light) palette. `Theme.overlay` and `Theme.dialog` are kept as
separate, non-overlapping namespaces so migrating a widget can never
accidentally bleed one surface's colors into the other.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget


class _Overlay:
    """Tokens for the feedback panel's dark overlay surface."""

    background = "#1e1e1e"
    text = "#e0e0e0"
    surface = "#252525"  # QTextEdit background
    button_background = "#333"
    button_hover = "#444"
    muted_text_dim = "#aaa"

    def apply_to(self, widget: QWidget) -> None:
        """Apply this surface's base background/text/textedit styling to `widget`."""
        widget.setStyleSheet(
            f"QWidget {{ background: {self.background}; color: {self.text}; }}"
            f"QTextEdit {{ background: {self.surface}; border: none; }}"
        )


class _Dialog:
    """Tokens for native QDialog/QWidget surfaces (system default light palette)."""

    card_background = "#fffde7"
    card_border = "#f9a825"
    warning_text = "#d97706"
    placeholder_background = "#cccccc"
    selection_border = "#d1d5db"
    selection_border_selected = "#3b82f6"
    lookback_border = "#4A90D9"

    def apply_placeholder(self, widget: QWidget) -> None:
        """Apply the flat placeholder background used when no thumbnail exists."""
        widget.setStyleSheet(f"background: {self.placeholder_background};")


class Theme:
    """Single source of truth for the app's visual tokens."""

    overlay = _Overlay()
    dialog = _Dialog()

    # Semantic status colors, shared across both surfaces (diagnostics checks,
    # settings connection tests, hotkey-conflict warnings).
    success = "green"
    danger = "red"
    warning = "orange"

    # Muted secondary-text color; identical on both surfaces today, so kept
    # as one shared token rather than duplicated in `_Overlay`/`_Dialog`.
    muted_text = "#888"

    # Spacing / font-size tokens for values currently hardcoded inline.
    font_size_small = "11px"
    border_radius = "4px"
    button_padding = "4px 10px"
    border_width_thin = "1px"
    border_width_thick = "2px"
