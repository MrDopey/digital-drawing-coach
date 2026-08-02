## Context

`_FrameRowWidget` in `history_panel.py` currently renders its delete button as a bare, unstyled 20×20 `QPushButton("×")`. Meanwhile `feedback_panel.py` establishes a button styling convention elsewhere in the app:

```python
self.setStyleSheet(
    "QWidget { background: #1e1e1e; color: #e0e0e0; }"
    "QTextEdit { background: #252525; border: none; }"
    "QPushButton { background: #333; border-radius: 4px; padding: 4px 10px; }"
    "QPushButton:hover { background: #444; }"
)
```

`_FrameRowWidget` already has one styling mechanism: `set_highlighted()` toggles a `border-left: 3px solid #4A90D9` (`_LOOKBACK_BORDER_STYLE`) via `setStyleSheet()` to mark rows inside the LLM's lookback window. Any new hover-highlight styling must coexist with this — both can be active on the same row at once (a lookback-window row can also be hovered), and neither should clobber the other via a raw `setStyleSheet()` overwrite.

`HistoryPanel`'s own dialog chrome (background, `_info_label`, `_hint_label`, `QListWidget`) stays on the OS default palette — this change does not touch it.

## Goals / Non-Goals

**Goals:**
- Restyle the delete button to look like the app's other buttons (rounded, padded, themed hover) rather than a bare 20×20 "×".
- Add a background hover-highlight on `_FrameRowWidget` rows that works correctly alongside the existing lookback border indicator and the existing hover-reveal of the delete button.

**Non-Goals:**
- No re-theming of `HistoryPanel`'s dialog chrome (background, labels, list widget) — it stays on the OS default palette. Only the delete button and row hover-highlight are in scope.
- No change to the delete/open interaction logic (double-click to open, click × to delete) — only visual styling.
- No introduction of a shared/global QSS file or theming system for the whole app — match the existing per-widget `setStyleSheet()` convention already used elsewhere.
- No change to `CaptureEngine`, `CapturedFrame`, or session data.

## Decisions

**Combine hover-highlight and lookback-border into one derived stylesheet, not two independent `setStyleSheet()` calls.**
`_FrameRowWidget` will track both `_is_hovered` and `_is_lookback` as booleans and recompute a single stylesheet string from both whenever either changes, rather than having the `eventFilter` hover handler and `set_highlighted()` independently call `setStyleSheet()` with unrelated fragments (which would let one clobber the other's rule). Alternative considered: use a Qt dynamic property (`setProperty("hovered", True)`) plus QSS attribute selectors (`_FrameRowWidget[hovered="true"]`) driven from a stylesheet set once on `HistoryPanel`. Rejected for this change — it's a bigger structural shift than the app's existing per-widget inline-stylesheet convention, and `_LOOKBACK_BORDER_STYLE`'s current border-left approach already relies on plain `setStyleSheet()` calls, so a combined-string approach is the smaller, more consistent diff.

**Style the delete button inline on `_FrameRowWidget.delete_button`, matching `feedback_panel.py`'s button convention (`border-radius: 4px`, themed background, `:hover` state) rather than introducing new colors.** Reuses the `#333`/`#444` pair already established for buttons elsewhere so the delete button doesn't introduce a fourth ad hoc color scheme.

## Risks / Trade-offs

- [Combining hover + lookback state into one stylesheet string touches `set_highlighted()`, which `_update_lookback_indicator()` calls on every `_render()`] → Keep `set_highlighted()`'s external signature/behavior identical; only its internal implementation changes to update shared state and recompute the combined style, so callers are unaffected.
- [Row hover-highlight and delete-button-visible-on-hover both key off the same `Enter`/`Leave` events in `eventFilter`] → Handle both effects in the same event branch so they stay in sync; no new event wiring needed.
- [QListWidget's own selection/hover styling could visually conflict with the row widget's custom hover background] → Since rows use `setItemWidget()` with a custom `_FrameRowWidget`, the list widget's own item painting is not visible under it; only the widget's own background applies, so no conflict expected.
- [The delete button now uses the app's dark button palette (`#333`/`#444`) while `HistoryPanel`'s own background stays on the OS default (typically light) palette] → Intentional per this change's scope: the button matches app-wide button conventions even though the dialog isn't re-themed. If this visual mismatch reads as odd once implemented, dialog-level theming can be proposed as a separate follow-up change.
