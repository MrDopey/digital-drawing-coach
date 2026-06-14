## MODIFIED Requirements

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

#### Scenario: API key is stored securely
- **WHEN** the API key is saved
- **THEN** the system stores it using the platform's keychain or a local encrypted config file, NOT plain text
