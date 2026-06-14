## MODIFIED Requirements

### Requirement: API key is stored securely
The system SHALL store the API key entered via the settings dialog in a `.env` file located in the XDG config dir (e.g., `~/.config/drawing-coach/.env`), using `dotenv.set_key()` for atomic writes. The platform keyring is not used.

#### Scenario: API key is saved via settings dialog
- **WHEN** the user enters an API key and saves settings
- **THEN** the system writes the key to `~/.config/drawing-coach/.env` as `DRAWING_COACH_API_KEY=<value>`

#### Scenario: API key is cleared via settings dialog
- **WHEN** the user clears the API key field and saves settings
- **THEN** the system removes `DRAWING_COACH_API_KEY` from the `.env` file using `dotenv.unset_key()`

## REMOVED Requirements

### Requirement: Keyring fallback for API key storage
**Reason**: Keyring dependency removed. API key storage is now exclusively via `.env` file and environment variables.
**Migration**: Users with a key stored in the system keyring must re-enter it once in the settings dialog (or add it to `~/.config/drawing-coach/.env` manually). The old keyring entry can be cleaned up with `keyring delete drawing-coach api_key`.
