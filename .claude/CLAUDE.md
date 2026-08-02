# Drawing Coach — Claude Code Guide

## Project Overview

**Drawing Coach** is an AI-powered desktop app that watches a digital drawing session and delivers real-time coaching feedback via a vision LLM. It captures screenshots periodically, detects inactivity, and returns suggestions as text or as correction lines drawn directly onto the canvas.

Two runtime modes:
- **GUI mode** — PyQt6 desktop window with feedback panel, session history, and system tray icon

## UI Conventions (PyQt6)

Dialogs must be resizable: content reflows correctly when the user drags the window edge.

- Style new widgets via the design system, not a one-off `setStyleSheet()` call: colors/spacing/font-size tokens live in `theme.py` (`Theme.overlay` for the dark feedback-panel surface, `Theme.dialog` for every other native dialog, plus shared semantic tokens like `Theme.success`/`Theme.danger`/`Theme.warning`/`Theme.muted_text`), and `design_system.py` provides `Card`, `PillBadge`, `MutedLabel`, `SectionHeader`, `PrimaryButton`, `IconButton` built on those tokens. `tests/test_design_system_compliance.py` fails the build on a stray hex literal or raw `setStyleSheet()` call outside those two files (escape hatch: a trailing `# theme-exempt` comment, for a value that must vary at runtime or isn't a UI theme color at all).
- Expanding widgets need a stretch factor: `layout.addWidget(w, 1)` — without it they don't grow when the dialog is resized
- Word-wrapped `QLabel`s in grid layouts need `setMinimumWidth(1)` — without it they lock the minimum layout width
- Selectable `QLabel`s need `setTextInteractionFlags(TextSelectableByMouse | TextSelectableByKeyboard)` — without it users cannot copy displayed text
- Scrollable content: `QScrollArea(setWidgetResizable=True, frameShape=NoFrame)`; no hardcoded dialog heights
- Child dialogs opened from a modal parent must use `exec()` not `show()` — `show()` inside an `exec()` loop cannot receive focus
- A scaled pixmap in a stretch-factored widget needs a `resizeEvent` override to re-scale it — without one, the image only updates on its next content change, not on window resize (unless the widget is meant to hold zoom/pan state independent of its container size, e.g. inside a `QScrollArea`, in which case it should *not* auto-rescale on resize)
- A widget with more than one independent visual state driven by `setStyleSheet()` (e.g. a hover highlight plus a separate persistent indicator) must track each state as its own field and recompute one combined stylesheet string from all of them — two handlers each calling `setStyleSheet()` on their own will clobber each other instead of composing
- A `QSplitter` pane that should sometimes disappear (e.g. no image to show) should be `hide()`/`show()`'d directly — Qt automatically excludes a hidden child (and its handle) from the splitter's layout, no manual `setSizes([0, ...])` needed
- A window that hides itself to the system tray instead of closing (`closeEvent` → `event.ignore()` + `self.hide()`) must give an explicit way back: a tray menu action (and ideally double-clicking the tray icon) that calls `show()` / `raise_()` / `activateWindow()` on the existing window instance — otherwise the only way back is to quit and relaunch
- A native `QTreeWidget`/`QListWidget` (rows are plain items, not a custom `setItemWidget()` per row) gets a row hover-highlight via one `::item:hover { background: ...; color: ...; }` stylesheet rule set once at construction time, with colors read from `self.palette()` (`QPalette.ColorRole.Highlight`/`HighlightedText`) so it follows the OS's active theme — same runtime-derived-color convention as the custom-row-widget hover pattern above, just via QSS instead of an `eventFilter`, since the item view already tracks per-item hover state natively

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| GUI | PyQt6, pynput |
| LLM | LiteLLM (supports OpenAI, Anthropic, Ollama, etc.) — feedback requests prefer LiteLLM structured JSON output (`response_format` json-schema) and try it once per app launch; on failure, a process-lifetime flag in `feedback_engine.py` disables it for the rest of the run and the app falls back to prose-plus-regex parsing (with a one-time user warning) |
| Image processing | Pillow, mss (Windows/Linux window capture), numpy |
| Window capture | `WindowBackend.capture_image()` (`window_manager.py`) — Windows/Linux use `mss.grab()` on the window rect; **macOS uses direct CoreGraphics** (`_backend_macos.py`, `CGWindowListCreateImage` scoped to the window ID) instead of `mss`, because `mss`'s macOS backend captures a screen *region* (compositing whatever else is on-screen there) rather than one window's content |
| Config | `ConfigManager` (`config_manager.py`) — single load/save owner; merges `config.json`, `.env`, and env vars with explicit precedence |
| Secrets | python-dotenv (`.env` in XDG config dir) — API key only; written by `ConfigManager.save()` |
| Long-term memory | `MemoryStore` (`memory_store.py`) — `memory.json` (raw cross-session drawing observations) and `memory_summaries.json` (their periodic re-summarisation history); this is app data feeding the coaching LLM's prompt, unrelated to and separate from Claude Code's own memory/auto-memory system |
| Tests | pytest, pytest-qt — on Linux/headless, `pynput` (imported by `hotkey_manager.py`) probes for a real X connection at import time even under `QT_QPA_PLATFORM=offscreen`, so any test importing it (directly or via `main_window.py`) needs a real or virtual display: `xvfb-run -a uv run pytest`. PyQt6 itself is an optional extra (`uv sync --extra gui`), not installed by a bare `uv sync` |
| Build | hatchling, PyInstaller |
| Release | `.github/workflows/release.yml` — manually dispatched (`workflow_dispatch` with a required `bump: patch\|minor\|major` input), not triggered by pushing a `v*` tag. `pyproject.toml`'s `[project].version` is the single authoritative version source (always semver); `scripts/build_version.py` reads it into `src/drawing_coach/_version.py` at build time, and `scripts/bump_version.py <bump>` applies the release-time bump. The workflow builds binaries embedding the current version, creates the `v<version>` GitHub Release, then bumps `pyproject.toml` and commits the change back to `main` — so `main` always previews the next release's version. Binaries are GitHub Release assets only; the previous GHCR/OCI (`oras`) publishing has been removed. |
