### Requirement: ConfigManager loads from all sources with explicit precedence
The system SHALL provide a `ConfigManager` class with a `load()` method that reads configuration from real environment variables, `.env` file, and `config.json` in that priority order (highest to lowest). The load SHALL NOT happen at module import time.

#### Scenario: Real env var overrides .env and config.json
- **WHEN** `DRAWING_COACH_MODEL` is set in the shell environment AND a different value exists in `.env`
- **THEN** `config_manager.config.model` returns the shell environment value

#### Scenario: .env overrides config.json
- **WHEN** `DRAWING_COACH_MODEL` is set only in `.env` AND a different value exists in `config.json`
- **THEN** `config_manager.config.model` returns the `.env` value

#### Scenario: config.json used when no env var present
- **WHEN** neither `DRAWING_COACH_MODEL` nor a `.env` entry is set AND `config.json` contains a model value
- **THEN** `config_manager.config.model` returns the `config.json` value

#### Scenario: Defaults applied when nothing is configured
- **WHEN** no env var, `.env` entry, or `config.json` entry is present for a field
- **THEN** `config_manager.config` returns the field's built-in default value

#### Scenario: Missing .env file is tolerated
- **WHEN** the `.env` file does not exist
- **THEN** `ConfigManager.load()` completes without error and config.json / env var values are still applied

#### Scenario: Missing config.json is tolerated
- **WHEN** `config.json` does not exist
- **THEN** `ConfigManager.load()` completes without error and env var / `.env` values are still applied

---

### Requirement: ConfigManager exposes a unified typed config view
The system SHALL expose the merged configuration as a typed `LLMConfig` value object accessible via `config_manager.config`. All application code MUST read settings from this object rather than calling `os.environ` directly.

#### Scenario: Access merged config after load
- **WHEN** `ConfigManager.load()` has been called
- **THEN** `config_manager.config` returns an `LLMConfig` instance with all fields populated according to precedence

#### Scenario: Config not accessible before load
- **WHEN** `ConfigManager.load()` has NOT been called
- **THEN** accessing `config_manager.config` raises `RuntimeError` with a descriptive message

---

### Requirement: ConfigManager routes writes to the correct backing store
The system SHALL persist settings to the appropriate backing store: the `api_key` field SHALL be written to `.env` only; all other fields SHALL be written to `config.json`. The `api_key` SHALL never be written to `config.json`.

#### Scenario: Saving api_key writes to .env only
- **WHEN** `config_manager.save(config)` is called with a non-empty `api_key`
- **THEN** the `.env` file contains `DRAWING_COACH_API_KEY=<value>` AND `config.json` does NOT contain the key

#### Scenario: Clearing api_key removes it from .env
- **WHEN** `config_manager.save(config)` is called with an empty `api_key`
- **THEN** the `.env` file does NOT contain `DRAWING_COACH_API_KEY`

#### Scenario: Saving other fields writes to config.json
- **WHEN** `config_manager.save(config)` is called with a new `model` value
- **THEN** `config.json` reflects the new value AND the `.env` file is unchanged

---

### Requirement: ConfigManager accepts injected paths for testability
The system SHALL accept optional `config_path` and `dotenv_path` constructor arguments so tests can point `ConfigManager` at temporary directories without touching XDG config dirs.

#### Scenario: Custom paths used in tests
- **WHEN** `ConfigManager(config_path=tmp_path / "config.json", dotenv_path=tmp_path / ".env")` is instantiated
- **THEN** `load()` and `save()` operate exclusively on those paths

---

### Requirement: No import-time side effects from config loading
The system SHALL NOT call `load_dotenv()` or read any config files at module import time. The `llm_config` module SHALL be importable without triggering file I/O.

#### Scenario: Importing llm_config has no file I/O side effects
- **WHEN** `import drawing_coach.llm_config` is executed
- **THEN** no files are read and `os.environ` is unchanged

---

### Requirement: ConfigManager supports portable export and import
The system SHALL provide `export_portable(path)` and `import_portable(path)` methods on `ConfigManager` that serialise / deserialise user preferences (excluding `api_key`) to a portable JSON file.

#### Scenario: Export excludes api_key
- **WHEN** `config_manager.export_portable(path)` is called
- **THEN** the exported file does NOT contain `api_key`

#### Scenario: Import merges preferences into current config
- **WHEN** `config_manager.import_portable(path)` is called with a valid export file
- **THEN** the fields from the file are saved to `config.json` and `config_manager.config` reflects the new values
