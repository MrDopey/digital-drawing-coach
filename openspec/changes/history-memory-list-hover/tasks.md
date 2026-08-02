## 1. Memory Viewer Hover Highlight

- [ ] 1.1 In `MemoryViewerDialog.__init__` (`src/drawing_coach/memory_viewer.py`), after creating `self._tree`, compute the hover background/text colors from `self.palette()` (`QPalette.ColorRole.Highlight` / `HighlightedText`), same pattern as `_FrameRowWidget._apply_style()` in `history_panel.py`.
- [ ] 1.2 Apply a `QTreeWidget::item:hover { background: ...; color: ...; }` stylesheet to `self._tree` using those colors, tagged `# theme-exempt` (runtime palette-derived, not a static design-system token).
- [ ] 1.3 Confirm the rule visibly highlights observation (child) rows without needing changes to the delete button's own styling or to category header rows.

## 2. Verification

- [ ] 2.1 Manually exercise (or Xvfb-run) `MemoryViewerDialog` with sample observations and confirm rows highlight on hover and unhighlight on leave.
- [ ] 2.2 Manually exercise `HistoryPanel` and confirm its existing row hover-highlight from `session-history-redesign` still behaves correctly (no regression expected, no code changes anticipated there).
- [ ] 2.3 Run `tests/test_design_system_compliance.py` to confirm the new stylesheet line doesn't trip the stray-hex/raw-`setStyleSheet()` check (verify the `# theme-exempt` marker is honored).

## 3. Documentation

- [ ] 3.1 Update `README.md` to mention the memory viewer's row hover-highlight if the README documents the memory viewer's UI at all (developer-facing note, not user-facing changelog).
- [ ] 3.2 Update `.claude/CLAUDE.md`'s PyQt6 UI Conventions section if this change reveals a reusable convention (e.g. "native `QTreeWidget`/`QListWidget` rows needing OS-palette-derived hover highlight via `::item:hover` stylesheet, computed at construction time") that isn't already captured there.
- [ ] 3.3 Review `openspec/config.yaml` and propose changes only if this spec reveals a clear, recurring gap in the current rules; otherwise leave it unchanged.

## 4. Final Verification

- [ ] 4.1 Run `uv run pytest` and confirm all tests pass.
