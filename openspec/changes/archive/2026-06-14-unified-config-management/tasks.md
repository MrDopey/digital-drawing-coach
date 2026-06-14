## 1. Create ConfigManager

- [x] 1.1 Create `src/drawing_coach/config_manager.py` with a `ConfigManager` class that accepts optional `config_path` and `dotenv_path` constructor arguments (defaulting to XDG paths)
- [x] 1.2 Implement `ConfigManager.load()`: call `load_dotenv(override=False)`, read `config.json`, apply env var overrides for `DRAWING_COACH_MODEL`, `DRAWING_COACH_API_BASE`, `DRAWING_COACH_API_KEY`, return merged `LLMConfig` and store as `self.config`
- [x] 1.3 Implement `ConfigManager.save(config: LLMConfig)`: write all fields except `api_key` to `config.json`; write/remove `DRAWING_COACH_API_KEY` in `.env` via `set_key`/`unset_key`
- [x] 1.4 Implement `ConfigManager.export_portable(path)` and `ConfigManager.import_portable(path)` (move logic from `LLMConfig`)
- [x] 1.5 Guard `config_manager.config` so it raises `RuntimeError` if accessed before `load()` is called

## 2. Strip LLMConfig to a plain dataclass

- [x] 2.1 Remove the module-level `load_dotenv()` call from `llm_config.py`
- [x] 2.2 Remove `LLMConfig.load()`, `LLMConfig.save()`, `api_key` property and setter, `export_portable`, and `import_portable` from `LLMConfig`
- [x] 2.3 Remove dotenv imports (`load_dotenv`, `set_key`, `unset_key`) from `llm_config.py`

## 3. Trim env.py

- [x] 3.1 Remove `api_key()`, `set_api_key()`, `model()`, and `api_base()` from `env.py` (logic now lives in `ConfigManager`)
- [x] 3.2 Confirm `env.py` retains only `xdg_config_home()` and `xdg_data_home()` and that `paths.py` still imports correctly

## 4. Update main_window.py

- [x] 4.1 Replace `LLMConfig.load()` with `ConfigManager().load()` at startup; store the manager as `self._config_manager`
- [x] 4.2 Pass `self._config_manager` to `SettingsDialog` instead of (or alongside) the raw `LLMConfig` value object

## 5. Update settings_dialog.py

- [x] 5.1 Replace `config.save()` call with `config_manager.save(config)` in the Save handler
- [x] 5.2 Replace `config.export_portable(path)` and `config.import_portable(path)` calls with `config_manager.export_portable(path)` / `config_manager.import_portable(path)`
- [x] 5.3 Update `api_key` read/write to go through `config_manager.config.api_key` and `config_manager.save()`

## 6. Update tests

- [x] 6.1 Rewrite `test_llm_config.py` to test `LLMConfig` as a dataclass only (field defaults, no load/save)
- [x] 6.2 Rewrite `test_env.py` to test only `xdg_config_home()` and `xdg_data_home()`
- [x] 6.3 Add `tests/test_config_manager.py` covering: precedence chain, missing file tolerance, save routing (api_key → .env, other fields → config.json), runtime error before load, and export/import round-trip

## 7. Documentation

- [x] 7.1 Update `.claude/CLAUDE.md` to reflect that config loading now uses `ConfigManager` (Secrets section and any startup flow notes)
- [x] 7.2 Run `uv run pytest` and confirm all tests pass
