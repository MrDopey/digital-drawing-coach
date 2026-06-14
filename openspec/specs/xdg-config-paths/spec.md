# xdg-config-paths Specification

## Purpose
TBD - created by syncing change xdg-config-home-support. Update Purpose after archive.
## Requirements
### Requirement: Config directory respects XDG_CONFIG_HOME
On Linux and macOS the system SHALL resolve the config directory to `$XDG_CONFIG_HOME/drawing-coach/` (defaulting to `~/.config/drawing-coach/` when the variable is unset or empty). On Windows the system SHALL continue to use `~/.drawing-coach/`.

#### Scenario: XDG_CONFIG_HOME is set
- **WHEN** the app starts and `XDG_CONFIG_HOME` is set to a non-empty value on Linux or macOS
- **THEN** the config file is read from and written to `$XDG_CONFIG_HOME/drawing-coach/config.json`

#### Scenario: XDG_CONFIG_HOME is unset
- **WHEN** the app starts and `XDG_CONFIG_HOME` is not set on Linux or macOS
- **THEN** the config file is read from and written to `~/.config/drawing-coach/config.json`

#### Scenario: Running on Windows
- **WHEN** the app starts on Windows
- **THEN** the config file is read from and written to `~/.drawing-coach/config.json` (legacy path unchanged)

### Requirement: Session data directory respects XDG_DATA_HOME
On Linux and macOS the system SHALL resolve the session data directory to `$XDG_DATA_HOME/drawing-coach/sessions/` (defaulting to `~/.local/share/drawing-coach/sessions/` when the variable is unset or empty). On Windows the system SHALL continue to use `~/.drawing-coach/sessions/`.

#### Scenario: XDG_DATA_HOME is set
- **WHEN** the app starts and `XDG_DATA_HOME` is set to a non-empty value on Linux or macOS
- **THEN** session data is stored under `$XDG_DATA_HOME/drawing-coach/sessions/`

#### Scenario: XDG_DATA_HOME is unset
- **WHEN** the app starts and `XDG_DATA_HOME` is not set on Linux or macOS
- **THEN** session data is stored under `~/.local/share/drawing-coach/sessions/`
