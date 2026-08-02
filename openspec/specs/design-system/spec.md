# design-system Specification

## Purpose

Shared theme tokens (colors, spacing, font sizes) and reusable styled widget components that PyQt6 panels/dialogs compose instead of writing their own `setStyleSheet()` calls, so visual consistency is enforced by construction rather than by convention alone.

## Requirements

### Requirement: Centralized theme tokens
The system SHALL provide a single `theme` module exposing named color, spacing, and font-size tokens as the sole source of visual values for the application's UI code. The module SHALL expose at least two token namespaces — one for the dark overlay surface used by the always-on-top feedback panel, and one for native dialog surfaces used elsewhere in the app — plus shared semantic status tokens (success, danger, warning) usable from either surface.

#### Scenario: A component reads a color from the theme module
- **WHEN** a widget needs a color value (e.g. a border, background, or text color)
- **THEN** it SHALL reference a named token from the `theme` module rather than a hardcoded hex literal

#### Scenario: Overlay and dialog tokens remain distinct namespaces
- **WHEN** the feedback panel (overlay surface) and a settings/history dialog (native surface) each request their background color from the theme module
- **THEN** the theme module SHALL return the overlay's existing dark value and the dialog's existing native/light value respectively, without either namespace overriding the other

#### Scenario: A status label requests a semantic status color
- **WHEN** code needs to indicate success, failure, or a warning state (e.g. a diagnostics check result or a connection test result)
- **THEN** it SHALL reference the shared `success`, `danger`, or `warning` token rather than hardcoding `"green"`, `"red"`, or `"orange"`

### Requirement: Reusable styled widget components
The system SHALL provide a small set of reusable widget classes — at minimum `Card`, `PillBadge`, `SectionHeader`, and `PrimaryButton` — that encapsulate their own styling internally, sourced from the `theme` module, so that callers compose them without writing their own `setStyleSheet()` calls or hex literals. Additional narrowly-scoped components MAY be added (e.g. `MutedLabel` for recurring secondary-text coloring, `IconButton` for small fixed-size icon-only buttons) when an existing call site's pattern doesn't fit any of the four named components and doesn't warrant a one-off exemption.

#### Scenario: A panel needs a bordered container
- **WHEN** a panel needs a visually distinct bordered/background container (e.g. a card-like grouping of controls)
- **THEN** it SHALL instantiate the shared `Card` component instead of building a `QFrame` with a hand-written stylesheet

#### Scenario: A panel needs a small colored status indicator
- **WHEN** a panel needs a small pill-shaped or colored status/label element (e.g. a selection indicator or status badge)
- **THEN** it SHALL instantiate the shared `PillBadge` component instead of hand-rolling equivalent styling on a plain `QLabel`

#### Scenario: Component internals change without call-site changes
- **WHEN** a design token used by a shared component (e.g. `Card`'s border color) is updated in the `theme` module
- **THEN** every call site using that component SHALL reflect the updated value without any call site being edited

### Requirement: No stray inline styling in migrated files
Once a file has been migrated to the design system, it SHALL NOT contain `setStyleSheet()` calls with inline hex color literals for values covered by the theme module or shared components.

#### Scenario: Migrated file is checked for inline hex literals
- **WHEN** `src/drawing_coach/feedback_panel.py`, `history_panel.py`, `main_window.py`, `session_picker_dialog.py`, `settings_dialog.py`, or `diagnostics.py` is searched for hex color literals (`#[0-9a-fA-F]{3,6}`) after migration
- **THEN** no matches SHALL remain outside of `theme.py` itself, except for (a) a value that must vary at runtime in a way a static token cannot express, or (b) a color that isn't a UI theme value at all (e.g. a decorative color used to render a drawn icon/asset) — either SHALL be marked with a `# theme-exempt` comment and a brief reason

#### Scenario: A decorative, non-theme color is exempted
- **WHEN** code draws a fixed-color decorative asset (e.g. `MainWindow._make_tray_icon`'s hand-drawn pencil glyph) using `QColor`/`QPen` hex literals that have no relationship to the app's light/dark UI palette
- **THEN** each such line MAY be marked `# theme-exempt` with a comment noting it's a decorative/icon color rather than a UI theme value, and the compliance check SHALL NOT flag it

### Requirement: Automated compliance enforcement
The system SHALL provide an automated check that fails when a file outside `theme.py` (and the component module) contains a hex color literal or a raw `setStyleSheet()` call without an explicit `# theme-exempt` escape-hatch comment. This check SHALL run in continuous integration on every push and pull request, and SHALL additionally be available as an opt-in local `pre-commit` git hook, implemented as a Python script that invokes the project's existing `uv run pytest` toolchain, blocking the commit when a violation is detected. CI SHALL remain the authoritative enforcement layer regardless of whether a given contributor has installed the local hook.

#### Scenario: CI fails on a reintroduced hex literal
- **WHEN** a pull request adds a hardcoded hex color literal to `history_panel.py` without a `# theme-exempt` comment
- **THEN** the CI test workflow SHALL fail, blocking the merge

#### Scenario: Escape hatch is honored
- **WHEN** a line contains a hex color literal or `setStyleSheet()` call marked with a trailing `# theme-exempt` comment
- **THEN** the compliance check SHALL NOT flag that line as a violation

#### Scenario: Pre-commit hook blocks a violating local commit
- **WHEN** a contributor with the local hook installed runs `git commit` on a change that violates the compliance check
- **THEN** the hook SHALL abort the commit before it is created and print the offending file and line to the terminal

#### Scenario: Pre-commit hook degrades gracefully without uv
- **WHEN** the local hook runs on a machine where `uv` is not available on `PATH`
- **THEN** the hook SHALL print a message stating the local check was skipped and that CI will still enforce it, and SHALL NOT block the commit on that basis alone

### Requirement: Migration preserves existing visual appearance
Adopting the design system SHALL NOT change the rendered appearance or behavior of any migrated panel or dialog.

#### Scenario: Feedback panel retains its dark overlay appearance after migration
- **WHEN** `feedback_panel.py` is migrated to use theme tokens and shared components
- **THEN** the feedback panel SHALL render with the same dark background, text, and button colors it had before migration

#### Scenario: History panel row selection/hover indicators retain their appearance after migration
- **WHEN** `history_panel.py` is migrated to use theme tokens and shared components
- **THEN** the lookback-window border indicator and any row hover/selection styling SHALL render with the same colors and visual treatment they had before migration
