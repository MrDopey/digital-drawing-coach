## 1. Row hover-highlight + delete button restyle

- [ ] 1.1 Add `_is_hovered` and `_is_lookback` state fields to `_FrameRowWidget` and a single method that recomputes one combined stylesheet string from both (background highlight + `_LOOKBACK_BORDER_STYLE` border), replacing the current unconditional `setStyleSheet(_LOOKBACK_BORDER_STYLE if highlighted else "")` in `set_highlighted()`
- [ ] 1.2 Update `eventFilter`'s `Enter`/`Leave` handling to set `_is_hovered` and trigger the combined-style recompute, alongside the existing `delete_button.setVisible(...)` toggle
- [ ] 1.3 Update `set_highlighted()` to set `_is_lookback` and trigger the combined-style recompute instead of calling `setStyleSheet()` directly, keeping its external signature unchanged
- [ ] 1.4 Restyle `delete_button` with rounded corners and the app's themed button colors (`#333` background, `#444` hover), matching `feedback_panel.py`'s `QPushButton` styling
- [ ] 1.5 Manually verify in the running app: hovering a row highlights its background and reveals the delete button; hovering a lookback-window row shows both the highlight and the left border at once; leaving a row clears the highlight

## 2. Tests

- [ ] 2.1 Add/update a `pytest-qt` test asserting a lookback-window row keeps its border indicator style present after a hover enter/leave cycle (regression guard for the combined-stylesheet logic)
- [ ] 2.2 Add a `pytest-qt` test asserting `_FrameRowWidget`'s stylesheet changes on `Enter`/`Leave` events (hover highlight applied and cleared)

## 3. Documentation

- [ ] 3.1 Update README.md with a developer-facing note on the Session History row's hover-highlight behavior, if the README documents that dialog's UI
- [ ] 3.2 Update `.claude/CLAUDE.md`'s PyQt6 UI Conventions section if this change surfaces a new reusable convention (e.g. combining multiple `setStyleSheet()`-driven visual states on one widget without clobbering)
- [ ] 3.3 Review `openspec/config.yaml` and propose changes only if this spec reveals a clear, recurring gap in the current rules (high threshold — skip if not clearly warranted)
- [ ] 3.4 Run `uv run pytest` and confirm all tests pass
