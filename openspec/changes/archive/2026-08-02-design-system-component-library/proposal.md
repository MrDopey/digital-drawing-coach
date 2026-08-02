## Why

Styling is currently duplicated across six PyQt6 files (`feedback_panel.py`, `history_panel.py`, `main_window.py`, `session_picker_dialog.py`, `settings_dialog.py`, `diagnostics.py`) as 22+ independent `setStyleSheet()` calls, each hardcoding its own hex color literals. Near-duplicate but non-identical shades of the same intended color (e.g. several distinct greys used where one border color was likely intended) have already drifted apart, and every new panel repeats the same ad-hoc styling work instead of reusing anything. As the app grows, this divergence will compound and make visual consistency harder to maintain or verify.

## What Changes

- Introduce a `theme` module defining the app's palette, spacing, and font-size tokens as the single source of truth for visual values (replacing inline hex literals).
- Introduce a small set of reusable styled widget classes (e.g. `Card`, `PillBadge`, `SectionHeader`, `PrimaryButton`) that encapsulate their own consistent appearance internally, sourced from the theme module.
- Migrate `feedback_panel.py` and `history_panel.py` to compose the new components, since they are the most actively developed panels and carry the widest variety of ad-hoc styles today.
- Migrate `main_window.py`, `session_picker_dialog.py`, `settings_dialog.py`, and `diagnostics.py` to compose the new components, removing their remaining inline `setStyleSheet()` calls and hardcoded hex values.
- Add an automated compliance check (pytest test scanning for stray hex literals / `setStyleSheet()` calls) enforced in a new CI workflow, plus an opt-in local Python `pre-commit` hook (driven by the project's existing `uv`/`pytest` toolchain) that blocks a violating commit before it's created — so consistency is enforced going forward, not just documented.
- **BREAKING**: none — this is an internal refactor of how existing UI is styled; no user-facing behavior, layout, or visual appearance is intended to change.

## Capabilities

### New Capabilities
- `design-system`: Shared theme tokens (colors, spacing, font sizes) and reusable styled widget components (`Card`, `PillBadge`, `SectionHeader`, `PrimaryButton`) that other panels compose instead of writing their own `setStyleSheet()` calls.

### Modified Capabilities
(none — existing capabilities' observable requirements are unchanged; only their styling implementation is consolidated)

## Impact

- Affected code: `src/drawing_coach/feedback_panel.py`, `src/drawing_coach/history_panel.py`, `src/drawing_coach/main_window.py`, `src/drawing_coach/session_picker_dialog.py`, `src/drawing_coach/settings_dialog.py`, `src/drawing_coach/diagnostics.py`
- New module(s): `src/drawing_coach/theme.py` (or `design_system/` package) providing tokens and reusable widget classes
- New files: `tests/test_design_system_compliance.py`, `.github/workflows/test.yml` (repo currently has no CI test gate, only a release-tag build workflow), `hooks/pre-commit` (Python), `scripts/install_git_hooks.sh`
- No new dependencies; PyQt6 only
- No changes to persisted config, `.env`, or `memory.json` formats
- Existing tests in `tests/` that assert on widget styling (e.g. `tests/test_history_panel.py`) will need updates to reference the new shared components rather than per-widget stylesheet strings
