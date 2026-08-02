## Context

`HistoryPanel` (`history_panel.py`) already has a row hover-highlight, added in the archived `session-history-redesign` change: each row is a custom `_FrameRowWidget` installed via `QListWidget.setItemWidget()`, which watches `QEvent.Type.Enter`/`Leave` on itself and recomputes a combined stylesheet (hover background + lookback border) using the live `QPalette.ColorRole.Highlight` / `HighlightedText` colors — so the highlight always matches the OS's current accent color rather than a hardcoded hex value. That file is `# theme-exempt` for this specific `setStyleSheet()` call since the color is runtime-derived, not a static design-system token.

`MemoryViewerDialog` (`memory_viewer.py`) renders observations in a `QTreeWidget` where each row is a native `QTreeWidgetItem` (columns 0/1 are plain item text; column 2 holds a `QPushButton("Delete")` via `setItemWidget()`). Native Qt item views paint a subtle hover tint on `QTreeWidgetItem`s by default in most styles (via `Qt::WA_Hover` on the viewport), but it's faint, platform/style-dependent, and doesn't cover column 2 (the delete button sits on top of it with its own default, unstyled hover). There's no guarantee it reads as "the row is highlighted" the way `HistoryPanel`'s explicit, palette-colored background does.

## Goals / Non-Goals

**Goals:**
- Give each memory-viewer observation row an explicit, visible background hover-highlight, driven by the same runtime `QPalette.Highlight`/`HighlightedText` colors `HistoryPanel` uses, so both windows feel consistent and the effect isn't at the mercy of the OS style's default (which may be absent, e.g. under some Linux styles/Xvfb-based test environments).
- Cover the full row width, including the column holding the delete button, not just the plain-text columns.

**Non-Goals:**
- No restyling of the "Delete" button itself (its own hover state, borders, etc.) — out of scope, matches this change's narrow focus on row-background hover.
- No conversion of the tree's category/date/note rendering to a fully custom widget (like `_FrameRowWidget`) — the existing `QTreeWidgetItem` + one embedded button structure stays; we only add hover styling on top of it.
- No re-theming of the dialog's other chrome (notes `QTextEdit`, buttons row) — stays on the OS default palette, same scoping precedent as `session-history-redesign`.
- No change to `MemoryStore`, observation data, or delete/export/clear-all logic.

## Decisions

**Use a `QTreeWidget::item:hover { background: ...; color: ...; }` stylesheet rule computed from `self.palette()` at dialog construction time, set once via `self._tree.setStyleSheet(...)`, rather than reimplementing per-row `Enter`/`Leave` event filters like `_FrameRowWidget`.**
`QTreeWidget` already tracks hover state per item natively (unlike `HistoryPanel`, which paints custom widgets over the list and must track hover itself); a QSS `:hover` pseudo-state rule is the smaller, idiomatic diff for a native item view. The color values are still computed from the live `QPalette` (not hardcoded), preserving the "hover matches the OS accent color" behavior established for the history panel, and the line gets the same `# theme-exempt` treatment as `history_panel.py`'s equivalent line, since it's a runtime-derived color rather than a static design-system token.
Alternative considered: replace the tree's per-row rendering with a custom widget per row (mirroring `_FrameRowWidget`), giving fully uniform control including under the delete button. Rejected — bigger structural change to `MemoryViewerDialog` than this fix warrants (the tree currently mixes native items and one embedded button; changing that structure isn't necessary to add a hover highlight and would touch export/delete wiring unnecessarily).

**Accept that the delete button's own area may not visually pick up the `::item:hover` background** (a `QPushButton` paints its own background on top of the item), and leave the button's own appearance unchanged (Non-Goal above). If this reads as visually incomplete once implemented, restyling the button to match `IconButton`/`HistoryPanel`'s delete button can be proposed as a follow-up, same pattern the prior design used for deferring dialog-chrome theming.

## Risks / Trade-offs

- [Native per-style hover tinting could visually stack with the new explicit `:hover` background, producing a doubled/uneven tint on some platforms] → The explicit background color is opaque and drawn by the same item delegate pass the native tint would have used, so it replaces rather than layers on the native tint in practice; verify visually once implemented (see Open Questions).
- [`QTreeWidget::item:hover` styling can behave inconsistently across rows that are `QTreeWidgetItem` top-level (category) rows vs. child (observation) rows] → Scope the rule so it visibly applies to observation (child) rows, the ones the user actually mouses over to find something to delete; category header rows aren't a click target that needs hover feedback.
- [The delete button's own default hover doesn't visually match the app's themed `IconButton` hover, which becomes more noticeable once the surrounding row hover looks intentional] → Accepted per Non-Goals; call out as a natural follow-up, not blocking this change.

## Open Questions

- Once implemented, confirm in a running (or Xvfb) session whether the delete-button column visually reads as "part of the highlighted row" or as a distracting gap — if the latter, a minimal transparent-background tweak on the button during hover may be worth a small follow-up rather than expanding this change's scope.
