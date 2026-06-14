# llm-config Specification

## Purpose
Defines how the user configures the LLM provider, model, API key, and base URL. API key storage uses a `.env` file in the XDG config dir (see `env-file-secrets` spec); the platform keyring is not used.
## Requirements
### Requirement: User configures LLM provider and model
The system SHALL provide a settings panel where the user can configure the LLM provider, model name, API key, and optional base URL. Configuration SHALL be validated before saving and persisted to a platform-appropriate config file whose location respects the XDG Base Directory Specification on Linux and macOS (see `xdg-config-paths` spec).

#### Scenario: User opens LLM settings
- **WHEN** the user opens the settings panel
- **THEN** the system displays fields for Model Name, API Key, and Base URL (optional)

#### Scenario: User saves valid configuration
- **WHEN** the user fills in at least Model Name and API Key and clicks Save
- **THEN** the system persists the configuration to the XDG-resolved config file and confirms with a success message

#### Scenario: User saves configuration with only model name (local model)
- **WHEN** the user fills in only Model Name (e.g. "ollama/llava") with no API key
- **THEN** the system saves the configuration without requiring an API key

#### Scenario: API key is saved via settings dialog
- **WHEN** the user enters an API key and saves settings
- **THEN** the system writes the key to `~/.config/drawing-coach/.env` as `DRAWING_COACH_API_KEY=<value>`

#### Scenario: API key is cleared via settings dialog
- **WHEN** the user clears the API key field and saves settings
- **THEN** the system removes `DRAWING_COACH_API_KEY` from the `.env` file using `dotenv.unset_key()`

### Requirement: LLM configuration is validated before use
The system SHALL verify the LLM configuration is valid before allowing feedback requests. If configuration is incomplete or invalid, the system SHALL direct the user to settings.

#### Scenario: No LLM configuration exists
- **WHEN** the user triggers feedback without having configured an LLM
- **THEN** the system displays "No LLM configured — open Settings to add your model details"

#### Scenario: User tests connection
- **WHEN** the user clicks "Test Connection" in settings
- **THEN** the system sends a minimal test prompt to the configured LLM and reports success or the specific error

### Requirement: LiteLLM-compatible base URL support
The system SHALL accept a custom base URL so users can point to LiteLLM proxy servers, Ollama instances, or other OpenAI-compatible endpoints.

#### Scenario: User sets a custom base URL
- **WHEN** the user enters a base URL (e.g. http://localhost:11434) and saves
- **THEN** all LLM calls use that base URL via LiteLLM's `api_base` parameter

#### Scenario: Base URL is left blank
- **WHEN** the user leaves the base URL field empty
- **THEN** the system uses the default endpoint for the configured provider

### Requirement: Configuration is portable via export/import
The system SHALL allow the user to export their LLM configuration (excluding the API key) to a file and import it on another machine.

#### Scenario: User exports configuration
- **WHEN** the user clicks "Export Config"
- **THEN** the system saves a JSON file with model name and base URL, explicitly excluding the API key

#### Scenario: User imports configuration
- **WHEN** the user selects an exported config file via "Import Config"
- **THEN** the system populates the model name and base URL fields; the user must re-enter the API key

