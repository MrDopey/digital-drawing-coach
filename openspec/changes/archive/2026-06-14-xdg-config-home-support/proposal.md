## Why

The app currently stores its config and session data at `~/.drawing-coach/`, ignoring the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/). On Linux (and by convention on macOS), tools should respect `XDG_CONFIG_HOME` so users can control where application config lives — important for dotfile management, containers, and multi-user setups.

## What Changes

- Config file path resolves via `XDG_CONFIG_HOME` (default `~/.config`) instead of hardcoded `~/.drawing-coach/`
- Session data path resolves via `XDG_DATA_HOME` (default `~/.local/share`) instead of hardcoded `~/.drawing-coach/`
- Windows behaviour is unchanged (no XDG on Windows; continues using `~/.drawing-coach/`)

## Capabilities

### New Capabilities

- `xdg-config-paths`: Config and session-data directories are resolved via XDG environment variables, with platform-appropriate fallbacks.

### Modified Capabilities

- `llm-config`: The "persisted to a local config file" requirement now specifies XDG_CONFIG_HOME-compliant path resolution on Linux/macOS.

## Impact

- `src/drawing_coach/llm_config.py` — `_CONFIG_PATH` and `_SESSIONS_DIR` constants replaced by a path-resolver function
- `src/drawing_coach/capture_engine.py` — `_SESSIONS_DIR` usage picks up the resolved path
- `tests/test_llm_config.py` — tests that patch `_CONFIG_PATH` need updating
- No dependency changes (stdlib `os`, `pathlib` sufficient; no new packages)
