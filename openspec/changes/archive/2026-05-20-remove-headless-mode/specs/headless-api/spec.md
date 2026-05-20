## REMOVED Requirements

### Requirement: App starts in headless mode when launched with --headless flag
**Reason**: Headless mode is not useful for a drawing coach — the app's core use case always involves a human at a display. The feature added FastAPI/uvicorn weight with no real-world benefit.
**Migration**: Use the GUI mode (`python -m drawing_coach`). There is no replacement server path.

### Requirement: Health endpoint confirms server is running
**Reason**: Removed with the headless server.
**Migration**: N/A — no server to health-check.

### Requirement: Capture endpoint triggers a screenshot
**Reason**: Removed with the headless server.
**Migration**: Screenshots are triggered automatically by the capture engine in GUI mode.

### Requirement: Feedback endpoint triggers LLM feedback on the latest capture
**Reason**: Removed with the headless server.
**Migration**: Feedback is requested via the GUI panel or the global hotkey (Ctrl+Shift+F).

### Requirement: Config endpoint reads and updates LLM configuration
**Reason**: Removed with the headless server.
**Migration**: Configuration is managed via the Settings dialog in the GUI.
