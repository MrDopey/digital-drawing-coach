## ADDED Requirements

### Requirement: App loads secrets from a .env file at startup
The system SHALL call `load_dotenv()` at module load time, pointing at the XDG config dir (e.g., `~/.config/drawing-coach/.env`), with `override=False` so real environment variables always take precedence over `.env` file values.

#### Scenario: .env file exists with API key
- **WHEN** a `.env` file exists at the config dir path containing `DRAWING_COACH_API_KEY=sk-...`
- **THEN** the system loads that value into the process environment before any config is read

#### Scenario: No .env file present
- **WHEN** no `.env` file exists at the config dir path
- **THEN** the system starts normally without error; `load_dotenv()` is a no-op

#### Scenario: Real environment variable overrides .env file
- **WHEN** `DRAWING_COACH_API_KEY` is set in the shell environment AND also present in the `.env` file
- **THEN** the shell-set value wins (`override=False` behaviour)

### Requirement: API key resolves exclusively from the environment
The system SHALL read the API key solely from the `DRAWING_COACH_API_KEY` environment variable (populated by dotenv or the calling shell). The platform keyring is not consulted.

#### Scenario: API key set via environment variable
- **WHEN** `DRAWING_COACH_API_KEY` is set in the environment
- **THEN** the system uses that value as the API key

#### Scenario: No API key in environment
- **WHEN** `DRAWING_COACH_API_KEY` is not set in the environment
- **THEN** the system returns an empty string for the API key

### Requirement: Settings dialog writes API key to .env file
The system SHALL persist the API key entered in the settings dialog to the `.env` file in the config dir using `dotenv.set_key()`. The keyring is not written.

#### Scenario: User saves a new API key in settings
- **WHEN** the user enters an API key and clicks Save in the settings dialog
- **THEN** the system writes `DRAWING_COACH_API_KEY=<value>` to `~/.config/drawing-coach/.env` and the value is readable on next startup

#### Scenario: User clears the API key in settings
- **WHEN** the user clears the API key field and clicks Save
- **THEN** the system removes the `DRAWING_COACH_API_KEY` entry from the `.env` file using `dotenv.unset_key()`

#### Scenario: Config directory is read-only
- **WHEN** the user attempts to save an API key and the config dir or `.env` file is not writable
- **THEN** the system surfaces a clear error message (e.g., "Could not save API key: permission denied") rather than silently failing

### Requirement: .env.example documents available variables
The system SHALL ship a `.env.example` file in the repository root listing all supported environment variables with descriptions and example values, so users know how to configure the app without reading source code.

#### Scenario: Developer clones the repo
- **WHEN** a developer clones the repository
- **THEN** they find a `.env.example` file at the root documenting `DRAWING_COACH_API_KEY`, `DRAWING_COACH_MODEL`, and `DRAWING_COACH_API_BASE`
