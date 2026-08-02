## 1. Theme Module

- [x] 1.1 Create `src/drawing_coach/theme.py` with `Theme.overlay` and `Theme.dialog` namespaces, populated with color values copied verbatim from current `setStyleSheet()` call sites (no new colors introduced)
- [x] 1.2 Add shared semantic status tokens (`success`, `danger`, `warning`) to `theme.py`, matching the existing `"green"` / `"red"` / `"orange"` values used in `diagnostics.py` and `settings_dialog.py`
- [x] 1.3 Add spacing and font-size tokens to `theme.py` for values currently hardcoded inline (e.g. `padding: 4px 10px`, `font-size: 11px`)

## 2. Shared Components

- [x] 2.1 Implement `Card(QFrame)` sourcing border/background from `theme.py`, replacing the hand-styled `QFrame` pattern in `session_picker_dialog.py`'s `_SessionRow` and `main_window.py`'s `_WriteErrorPopup`
- [x] 2.2 Implement `PillBadge(QLabel)` sourcing color from `theme.py`'s semantic status tokens, replacing the ad-hoc green/red/orange label coloring in `diagnostics.py` and `settings_dialog.py`
- [x] 2.3 Implement `SectionHeader(QLabel)` sourcing font weight/size from `theme.py`, replacing the bold title-label pattern in `feedback_panel.py`
- [x] 2.4 Implement `PrimaryButton(QPushButton)` sourcing background/hover/radius from `theme.py`'s overlay tokens, replacing `feedback_panel.py`'s inline `QPushButton` stylesheet block
- [x] 2.5 Write unit tests for each component covering: token values are applied, and overlay vs. dialog variants render distinct colors
- [x] 2.6 (Added during implementation, beyond the spec's named minimum) Implement `MutedLabel(QLabel)` — the recurring `#888`/`#aaa` secondary-text pattern noted in design.md Context point 2 doesn't fit Card/PillBadge/SectionHeader/PrimaryButton, so it gets its own small component rather than a one-off exemption in each of the four files that use it
- [x] 2.7 (Added during implementation) Implement `IconButton(QPushButton)` — history_panel.py's hover-reveal delete button is a small fixed-size icon-only button with no padding, distinct from `PrimaryButton`'s padded default; forcing it into `PrimaryButton` would visually clip the glyph

## 3. Migrate feedback_panel.py

- [x] 3.1 Replace `feedback_panel.py`'s inline `setStyleSheet()` block with `theme.py` overlay tokens and the new `SectionHeader`/`PrimaryButton` components
- [x] 3.2 Replace remaining inline hex/color literals (`#aaa`, `#888`, font-size strings) with theme tokens
- [x] 3.3 Update or add tests for `feedback_panel.py` to assert on component state rather than raw QSS strings

## 4. Migrate history_panel.py

- [x] 4.1 Replace `_LOOKBACK_BORDER` and `_DELETE_BUTTON_STYLE` with theme tokens and shared components as appropriate; leave `_FrameRowWidget._apply_style()`'s `QPalette.ColorRole.Highlight`/`HighlightedText` hover lookup untouched (it's a deliberate OS-theme-following exception, not a candidate for a static token — see design.md Non-Goals)
- [x] 4.2 Update any `tests/test_history_panel.py` assertions that check stylesheet strings for the lookback border / delete button to instead check component/semantic state; leave the existing `QPalette`-based hover-color assertions (lines ~239-262) unchanged
- [x] 4.3 Confirm the lookback-window border indicator and the theme-aware hover highlight still render identically (per design.md's visual-parity requirement)

## 5. Migrate Remaining Files

- [x] 5.1 Migrate `main_window.py` (`_WriteErrorPopup` to `Card`, status/hint labels to theme tokens)
- [x] 5.2 Migrate `session_picker_dialog.py` (`_SessionRow` selection styling to `Card`, muted date label to theme tokens)
- [x] 5.3 Migrate `settings_dialog.py` (connection-test label and hotkey-conflict label to `PillBadge`/theme tokens)
- [x] 5.4 Migrate `diagnostics.py` (check-result status labels to `PillBadge`, hint label to theme tokens)

## 6. Automated Enforcement

- [x] 6.1 Write `tests/test_design_system_compliance.py`: scans `src/drawing_coach/*.py` (excluding `theme.py` and the component module) for hex color literals (`#[0-9a-fA-F]{3,6}`) and raw `setStyleSheet(` calls, failing with the offending file/line unless the line carries a `# theme-exempt` escape-hatch comment
- [x] 6.2 Add `.github/workflows/test.yml` running `uv sync` + `uv run pytest` on push and pull request — the repo currently has no CI test gate (only `.github/workflows/release.yml`, which builds tagged binaries), so this is the layer that actually blocks a violating merge
- [x] 6.3 Add a tracked `hooks/pre-commit` Python script (`#!/usr/bin/env python3`) that shells out to `uv run pytest tests/test_design_system_compliance.py -q`, exits non-zero (blocking the commit) and prints file/line offenders on failure, and prints a "uv not found — CI will still enforce this" message and exits 0 if `uv` isn't on `PATH` — reuses the project's existing pytest/uv toolchain rather than a separate hook framework
- [x] 6.4 Add `scripts/install_git_hooks.sh` that runs `git config core.hooksPath hooks` so `hooks/pre-commit` is picked up without manual copying into `.git/hooks/`; make the script chmod the hook executable

## 7. Verification

- [x] 7.1 Grep `src/drawing_coach/` for `setStyleSheet` and hex literals (`#[0-9a-fA-F]{3,6}`); confirm no matches remain outside `theme.py` except explicitly commented runtime-varying exceptions
- [x] 7.2 Manually run the app and visually compare the feedback panel, history panel, session picker, settings dialog, and diagnostics dialog against their pre-migration appearance
- [ ] 7.3 Verify `tests/test_design_system_compliance.py` fails when a hex literal is temporarily reintroduced without the escape-hatch comment, then passes once removed (confirms the check has teeth)
- [ ] 7.4 After running `scripts/install_git_hooks.sh` locally, verify `git commit` is actually blocked by `hooks/pre-commit` on a violating change, and succeeds once fixed

## 8. Documentation

- [ ] 8.1 Update `README.md` from a developer's perspective to document the `theme.py` module, shared component classes, the compliance test, and the one-time `scripts/install_git_hooks.sh` setup step (including that `git commit --no-verify` skips the local hook, and that CI enforces regardless)
- [ ] 8.2 Update `.claude/CLAUDE.md`'s "UI Conventions (PyQt6)" section to reference the design-system module and shared components as the preferred way to style new widgets
- [ ] 8.3 Review `openspec/config.yaml` for a clear, recurring gap this change reveals in current rules; propose changes only if one is evident (high bar — skip if none)
- [ ] 8.4 Run `uv run pytest` and confirm all tests pass
