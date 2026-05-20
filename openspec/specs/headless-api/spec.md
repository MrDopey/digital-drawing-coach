# headless-api Specification

## Purpose
TBD - created by archiving change drawing-coach-distribution. Update Purpose after archive.
## Requirements
### Requirement: App starts in headless mode when launched with --headless flag
The system SHALL start a FastAPI HTTP server instead of the GUI when launched with the `--headless` flag or when the `DRAWING_COACH_HEADLESS=1` environment variable is set. No display server SHALL be required in headless mode.

#### Scenario: App launched with --headless flag
- **WHEN** the application is started with `python -m drawing_coach --headless` or the binary is run with `--headless`
- **THEN** the FastAPI server starts on the configured port (default: 8080) and the GUI is not initialised

#### Scenario: App launched with DRAWING_COACH_HEADLESS env var
- **WHEN** the application is started with `DRAWING_COACH_HEADLESS=1` in the environment
- **THEN** the server starts identically to the `--headless` flag case

#### Scenario: GUI-only modules are not imported in headless mode
- **WHEN** headless mode starts
- **THEN** PyQt6 and any GUI-only modules SHALL NOT be imported, allowing the server to run without a display or Qt installation

### Requirement: Health endpoint confirms server is running
The system SHALL expose `GET /health` that returns the application version and status.

#### Scenario: Health check succeeds
- **WHEN** `GET /health` is called
- **THEN** the response is `{"status": "ok", "version": "<embedded version>"}` with HTTP 200

### Requirement: Capture endpoint triggers a screenshot
The system SHALL expose `POST /capture` that triggers a manual screenshot of the configured drawing window and returns the frame path and timestamp.

#### Scenario: Capture succeeds with a configured window
- **WHEN** `POST /capture` is called and a drawing window is configured
- **THEN** the response is `{"frame_path": "<path>", "timestamp": "<iso8601>"}` with HTTP 200

#### Scenario: No window configured
- **WHEN** `POST /capture` is called and no drawing window is configured
- **THEN** the response is `{"error": "No drawing window configured"}` with HTTP 422

### Requirement: Feedback endpoint triggers LLM feedback on the latest capture
The system SHALL expose `POST /feedback` that triggers LLM feedback using the most recent captured frame(s) and returns the result. An optional `mode` field in the request body selects the feedback mode (default: `full_critique`).

#### Scenario: Feedback succeeds
- **WHEN** `POST /feedback` is called with at least one frame in the buffer
- **THEN** the response is `{"mode": "<mode>", "feedback": "<text>", "annotations": null|[...]}` with HTTP 200

#### Scenario: Feedback called with overlay mode
- **WHEN** `POST /feedback` is called with `{"mode": "overlay"}`
- **THEN** the `annotations` field in the response contains the parsed annotation array (or `null` on parse failure)

#### Scenario: No frames available
- **WHEN** `POST /feedback` is called before any capture has occurred
- **THEN** the response is `{"error": "No frames captured yet"}` with HTTP 422

### Requirement: Config endpoint reads and updates LLM configuration
The system SHALL expose `GET /config` to return the current non-sensitive configuration and `PUT /config` to update fields. The API key SHALL NOT be returned by `GET /config`.

#### Scenario: GET /config returns current settings
- **WHEN** `GET /config` is called
- **THEN** the response includes `model`, `api_base`, `lookback_frames`, `style_focus`, and other non-sensitive fields; `api_key` is omitted

#### Scenario: PUT /config updates a field
- **WHEN** `PUT /config` is called with `{"model": "gpt-4o"}`
- **THEN** the model is updated in the running config and the response echoes the updated non-sensitive config

#### Scenario: Environment variable config overrides file config
- **WHEN** `DRAWING_COACH_MODEL`, `DRAWING_COACH_API_KEY`, or `DRAWING_COACH_API_BASE` are set in the environment
- **THEN** those values take precedence over the config file for all LLM calls in headless mode

