## Context

Config and session directories are currently hardcoded to `Path.home() / ".drawing-coach"` in `llm_config.py`. On Linux and macOS, the XDG Base Directory Spec defines `XDG_CONFIG_HOME` (default `~/.config`) for config and `XDG_DATA_HOME` (default `~/.local/share`) for data. Ignoring these variables breaks dotfile managers, containerised workflows, and shared-home setups where users expect to control app directory locations via environment variables.

The two relevant paths are:
- `_CONFIG_PATH = ~/.drawing-coach/config.json`
- `_SESSIONS_DIR = ~/.drawing-coach/sessions/` (also used by `capture_engine.py`)

## Goals / Non-Goals

**Goals:**
- Resolve config to `$XDG_CONFIG_HOME/drawing-coach/config.json` (default `~/.config/drawing-coach/config.json`) on Linux/macOS
- Resolve sessions to `$XDG_DATA_HOME/drawing-coach/sessions/` (default `~/.local/share/drawing-coach/sessions/`) on Linux/macOS
- Leave Windows behaviour unchanged (no XDG convention; keep `~/.drawing-coach/`)

**Non-Goals:**
- Exposing config/session paths as user-configurable settings in the UI
- Supporting `XDG_CONFIG_DIRS` (read-only fallback list) — only `XDG_CONFIG_HOME` (writable home) is needed
- Migrating sessions if the user has already started using the XDG paths

## Decisions

### 1. Path resolver function instead of module-level constants

**Decision:** Replace the `_CONFIG_PATH` and `_SESSIONS_DIR` module-level constants with a single `_resolve_paths()` function that returns both paths.

**Rationale:** Module-level `Path` constants are evaluated at import time, so they cannot react to `XDG_CONFIG_HOME` being set after import (relevant for tests and CLI tools). A function is also trivially mockable in tests.

**Alternative considered:** `platformdirs` / `appdirs` library — adds a dependency and has its own opinions about macOS paths (`~/Library/…`) that diverge from XDG. Stdlib `os.environ` is sufficient.

### 2. Platform detection via `sys.platform`

**Decision:** Apply XDG logic only when `sys.platform != "win32"`. On Windows, fall back to `~/.drawing-coach/`.

**Rationale:** XDG is a Linux/freedesktop standard. macOS has its own convention (`~/Library/…`) but in practice many macOS developers prefer XDG-style `~/.config`. Treating macOS the same as Linux is common (e.g. fish shell, Neovim) and aligns with what the user actually expects.

### 3. Shared path module

**Decision:** Extract path logic into a dedicated `src/drawing_coach/paths.py` module that both `llm_config.py` and `capture_engine.py` import.

**Rationale:** Both modules currently use `~/.drawing-coach/` separately. Centralising avoids drift if a third consumer appears. The module is small (~30 lines) and has no external dependencies.

## Risks / Trade-offs

- **Tests that patch `_CONFIG_PATH` directly break** → Mitigation: update tests to patch `drawing_coach.paths.config_path()` or use the existing `tmp_path` fixture pattern.
- **macOS users who explicitly use `~/Library/…` are unaffected** → If `XDG_CONFIG_HOME` is unset, they get `~/.config/drawing-coach/` which is a reasonable default.

## Migration Plan

1. Ship `paths.py` with resolver logic
2. Update `llm_config.py` and `capture_engine.py` to import from `paths.py`
3. Update tests to patch at the `paths` module level
4. No database schema changes, no API changes — purely filesystem paths
5. Rollback: revert `paths.py` and restore the two hardcoded constants
