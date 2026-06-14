## Why

Config is split across three sources — `config.json`, `.env`, and real environment variables — with loading and writing logic scattered across `llm_config.py`, `env.py`, and `settings_dialog.py`. There is no single place that owns precedence, and keeping the three stores in sync requires manual coordination. The recent `fix: apikey desync` commit (66760b5) is a concrete example: saving the API key to `.env` didn't update `os.environ`, so subsequent reads returned the stale value. A central config manager eliminates this class of bug by making all writes go through one owner.

## What Changes

- Introduce a `ConfigManager` class that owns all config loading and writing: real env vars override `.env`, which overrides `config.json`, which falls back to defaults
- Remove the module-level `load_dotenv()` side effect from `llm_config.py`; replace with an explicit `ConfigManager.load()` call at application startup
- Consolidate the env-var reads (`env.api_key()`, `env.model()`, `env.api_base()`, `env.set_api_key()`) into `ConfigManager` — no more parallel read/write paths in `env.py`
- Expose a single `config` object so all callers (`main_window.py`, `settings_dialog.py`, coaches) read from one place
- **BREAKING**: `LLMConfig` loses its `load()`, `save()`, `api_key` property/setter, and `export_portable`/`import_portable` methods; it becomes a plain typed dataclass
- `ConfigManager.save()` handles persistence routing: secrets (`api_key`) → `.env` + `os.environ`; user preferences → `config.json` — both stores always in sync after a save

## Capabilities

### New Capabilities

- `config-manager`: Central config service — loads from all three sources with explicit precedence, exposes a unified typed settings view, routes writes to the correct backing store, and keeps `.env` / `config.json` / `os.environ` in sync

### Modified Capabilities

<!-- No existing spec-level requirements are changing — this is an internal refactor. -->

## Impact

- **`src/drawing_coach/config_manager.py`** (new) — `ConfigManager` class
- **`src/drawing_coach/llm_config.py`** — stripped to a plain dataclass; module-level `load_dotenv()` removed
- **`src/drawing_coach/env.py`** — `api_key()`, `set_api_key()`, `model()`, `api_base()` removed; only XDG path helpers remain
- **`src/drawing_coach/main_window.py`** — calls `ConfigManager.load()` at startup instead of `LLMConfig.load()`
- **`src/drawing_coach/settings_dialog.py`** — writes go through `ConfigManager.save()` rather than direct dotenv calls
- **Tests** — `test_llm_config.py`, `test_env.py` updated; new `test_config_manager.py` added
- **No new dependencies** — `python-dotenv` already in use
