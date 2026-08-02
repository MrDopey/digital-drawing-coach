"""Tests for the shared design-system widget components."""

from drawing_coach.design_system import (
    Card,
    IconButton,
    MutedLabel,
    PillBadge,
    PrimaryButton,
    SectionHeader,
)
from drawing_coach.theme import Theme


# ---------------------------------------------------------------------------
# Card
# ---------------------------------------------------------------------------


def test_card_applies_background_and_border(qtbot):
    card = Card(background=Theme.dialog.card_background, border=Theme.dialog.card_border)
    qtbot.addWidget(card)

    style = card.styleSheet()
    assert Theme.dialog.card_background in style
    assert Theme.dialog.card_border in style


def test_card_set_border_updates_style_without_background(qtbot):
    card = Card(border=Theme.dialog.selection_border, radius=Theme.border_radius)
    qtbot.addWidget(card)
    assert Theme.dialog.selection_border in card.styleSheet()

    card.set_border(Theme.dialog.selection_border_selected)
    assert Theme.dialog.selection_border_selected in card.styleSheet()
    assert Theme.dialog.selection_border not in card.styleSheet()


def test_card_omits_background_rule_when_not_given(qtbot):
    card = Card(border=Theme.dialog.selection_border)
    qtbot.addWidget(card)
    assert "background" not in card.styleSheet()


# ---------------------------------------------------------------------------
# PillBadge
# ---------------------------------------------------------------------------


def test_pill_badge_variants_map_to_theme_colors(qtbot):
    badge = PillBadge("ok", variant="success")
    qtbot.addWidget(badge)
    assert Theme.success in badge.styleSheet()

    badge.set_variant("danger")
    assert Theme.danger in badge.styleSheet()

    badge.set_variant("warning")
    assert Theme.warning in badge.styleSheet()

    badge.set_variant("neutral")
    assert badge.styleSheet() == ""


def test_pill_badge_explicit_color_overrides_variant(qtbot):
    badge = PillBadge("warn", color=Theme.dialog.warning_text)
    qtbot.addWidget(badge)
    assert Theme.dialog.warning_text in badge.styleSheet()


# ---------------------------------------------------------------------------
# MutedLabel
# ---------------------------------------------------------------------------


def test_muted_label_default_uses_shared_muted_text(qtbot):
    label = MutedLabel("hint")
    qtbot.addWidget(label)
    assert Theme.muted_text in label.styleSheet()


def test_muted_label_dim_uses_overlay_dim_variant(qtbot):
    label = MutedLabel("100%", dim=True)
    qtbot.addWidget(label)
    assert Theme.overlay.muted_text_dim in label.styleSheet()
    assert Theme.muted_text not in label.styleSheet()


def test_muted_label_small_adds_font_size(qtbot):
    label = MutedLabel("hint", small=True)
    qtbot.addWidget(label)
    assert Theme.font_size_small in label.styleSheet()


def test_muted_label_extra_style_is_appended(qtbot):
    label = MutedLabel("hint", extra_style="padding-left: 2px;")
    qtbot.addWidget(label)
    assert "padding-left: 2px;" in label.styleSheet()
    assert Theme.muted_text in label.styleSheet()


# ---------------------------------------------------------------------------
# SectionHeader
# ---------------------------------------------------------------------------


def test_section_header_is_bold(qtbot):
    header = SectionHeader("Title")
    qtbot.addWidget(header)
    assert "font-weight: bold" in header.styleSheet()


# ---------------------------------------------------------------------------
# PrimaryButton / IconButton — overlay-surface tokens, distinct from dialog tokens
# ---------------------------------------------------------------------------


def test_primary_button_uses_overlay_tokens(qtbot):
    btn = PrimaryButton("Go")
    qtbot.addWidget(btn)

    style = btn.styleSheet()
    assert Theme.overlay.button_background in style
    assert Theme.overlay.button_hover in style
    assert Theme.dialog.card_background not in style


def test_icon_button_is_fixed_size_with_no_padding(qtbot):
    btn = IconButton("x", size=24)
    qtbot.addWidget(btn)

    assert btn.size().width() == 24
    assert btn.size().height() == 24
    assert "padding" not in btn.styleSheet()
    assert Theme.overlay.button_background in btn.styleSheet()


def test_primary_button_and_icon_button_render_distinct_overlay_vs_dialog_colors(qtbot):
    # Overlay-surface components should never reach for dialog-surface tokens.
    primary = PrimaryButton("Go")
    icon = IconButton("x")
    qtbot.addWidget(primary)
    qtbot.addWidget(icon)

    for style in (primary.styleSheet(), icon.styleSheet()):
        assert Theme.dialog.card_background not in style
        assert Theme.dialog.selection_border not in style
