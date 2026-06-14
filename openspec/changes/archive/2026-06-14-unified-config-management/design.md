## Context

Config state is currently split across three sources with no single owner:

- **`config.json`** — user preferences (model, capture interval, hotkey, etc.) persisted via `LLMConfig.save()`; the only store the app writes to through the UI
- **`.env`** — secrets only; the app writes exactly one key here: `DRAWING_COACH_API_KEY` via `set_key`/`unset_key`
- **Real environment variables (and `.env` reads)** — deployment overrides (`DRAWING_COACH_MODEL`, `DRAWING_COACH_API_BASE`, `DRAWING_COACH_API_KEY`) set manually by the user or in CI/Docker; the app reads but never writes these

The current loading path has two problems:

1. `load_dotenv()` is called at **module import time** in `llm_config.py`, making initialization an implicit side-effect of the first `import drawing_coach.llm_config` — order-sensitive and invisible to callers.
2. `LLMConfig` is both a data class **and** a persistence layer **and** an env-var reader — three concerns in one class. The `api_key` property reads from `env.api_key()`, its setter writes to `.env` via dotenv, and `LLMConfig.load()` also reads `env.model()` / `env.api_base()` to apply overrides.

The result: callers cannot know which value they'll get without tracing three code paths.

## Goals / Non-Goals

**Goals:**
- Single explicit `ConfigManager.load()` call at application startup; no import-time side effects
- One object that exposes the merged, precedence-resolved view of all settings
- Clear persistence routing: secrets write to `.env`; user preferences write to `config.json`
- Testable in isolation: `ConfigManager` accepts injected paths so tests don't touch the real XDG dirs
- No new dependencies — `python-dotenv` is already in use

**Non-Goals:**
- Live reload / watching config files for changes at runtime
- Multi-profile or per-project config isolation
- Changing the `.env` / `config.json` file formats or location
- Encrypting secrets at rest

## Decisions

### Decision 1: ConfigManager is a class, not a module-level singleton

**Choice:** `ConfigManager` is instantiated once at startup (in `main_window.py`) and passed to components as a dependency, the same pattern already used for `LLMConfig`.

**Rationale:** A singleton makes unit-testing hard — it holds global state across tests. A class instance is cheap to create with custom `config_path` / `dotenv_path` arguments for test isolation. Passing it explicitly to `MainWindow`, `SettingsDialog`, and coaches makes dependencies visible.

**Alternative considered:** Module-level `_instance` accessor (`config_manager.instance()`). Rejected because it recreates the import-time ordering problem and makes test isolation require patching global state.

---

### Decision 2: env.py is kept as an XDG-path helper; env-var config reads move into ConfigManager

**Choice:** `env.py` retains `xdg_config_home()`, `xdg_data_home()`, and the operational env vars `log_level()`, `log_file()`, and `log_max_bytes()`. The `api_key()`, `model()`, `api_base()`, and `set_api_key()` functions are removed and their logic is absorbed into `ConfigManager`.

**Rationale:** `paths.py` depends on `env.py` for XDG resolution; removing it entirely would require merging path logic. The operational log vars (`DRAWING_COACH_LOG_LEVEL`, `DRAWING_COACH_LOG_FILE`, `DRAWING_COACH_LOG_MAX_BYTES`) have no UI or `config.json` equivalent — they are deployment-only knobs read at process startup, not user-facing config, so they belong in `env.py` rather than `ConfigManager`.

---

### Decision 3: Precedence chain is enforced inside ConfigManager.load()

**Choice:** `real env vars > .env > config.json > defaults`

Implementation:
1. Call `load_dotenv(dotenv_path=..., override=False)` — populates `os.environ` from `.env` only if not already set (preserves shell env vars)
2. Read `config.json` into a dict of defaults
3. For each field that has a corresponding env var (`DRAWING_COACH_MODEL`, `DRAWING_COACH_API_BASE`, `DRAWING_COACH_API_KEY`), check `os.environ` and override the config.json value if present

**Rationale:** This is the 12-factor pattern already partially in place. `override=False` means a real shell env var always wins, even if the same key is in `.env`.

---

### Decision 4: Persistence routing is explicit in ConfigManager.save()

**Choice:** `ConfigManager.save(config)` routes by field:
- `api_key` → `set_key` / `unset_key` on the `.env` file **and** `env.set_api_key()` to keep `os.environ` in sync; never written to `config.json`
- all other fields → serialised to `config.json`

`DRAWING_COACH_MODEL` and `DRAWING_COACH_API_BASE` are never written to `.env` by the app — if a user sets them there manually as deployment overrides, `ConfigManager.load()` will respect them, but saving from the UI always goes to `config.json`. This keeps a clean separation: the app manages `config.json` and the api_key secret; the operator manages env var overrides.

---

### Decision 5: LLMConfig becomes a plain frozen dataclass

**Choice:** `LLMConfig` keeps its field definitions and defaults but loses `save()`, `load()`, `api_key` property, and `export_portable` / `import_portable` methods. Those move to `ConfigManager`.

**Rationale:** Separates "shape of config" from "how config is loaded/saved". `LLMConfig` stays as the typed value object; `ConfigManager` is the service that produces and persists it.

## Risks / Trade-offs

- **Import-order assumptions in existing tests** → `test_llm_config.py` patches `os.environ` before the load_dotenv call; removing the module-level call changes when patching must happen. Mitigation: rewrite affected tests to call `ConfigManager.load()` explicitly with controlled env.
- **Settings dialog coupling** → `settings_dialog.py` calls `config.save()` and directly accesses `config.api_key`. Changing the save path requires updating the dialog. Mitigation: dialog change is mechanical; covered in tasks.
- **Export/import portable config** → currently lives on `LLMConfig`. Must move to `ConfigManager.export_portable()` / `import_portable()`. Mitigation: same logic, different owner.

## Migration Plan

1. Add `ConfigManager` in a new file (`config_manager.py`) alongside existing code — no callers change yet
2. Update `main_window.py` to instantiate `ConfigManager` and pass it down; keep a `LLMConfig`-compatible shim temporarily if needed
3. Remove module-level `load_dotenv()` from `llm_config.py`; strip `LLMConfig` to a dataclass
4. Update `settings_dialog.py` to call `ConfigManager.save()`
5. Remove `api_key`, `model`, `api_base`, `set_api_key` from `env.py`
6. Update tests

No rollback required — this is a local refactor with no external API surface. The `.env` and `config.json` file formats are unchanged.

## Open Questions

- Should coaches (`StuckCoach`, `CaptureManager`) receive `ConfigManager` directly or continue to receive the `LLMConfig` value object? Leaning toward passing the value object to keep coaches free of infrastructure concerns.
