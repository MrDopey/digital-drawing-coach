# system-diagnostics Specification

## Purpose
TBD - created by archiving change setup-diagnostics-button. Update Purpose after archive.
## Requirements
### Requirement: Diagnostics dialog accessible from Settings
The system SHALL provide a "Diagnostics…" button in the Settings dialog that opens a DiagnosticsDialog showing the status of all system health checks.

#### Scenario: User opens diagnostics from Settings
- **WHEN** the user opens the Settings dialog and clicks the "Diagnostics…" button
- **THEN** a non-modal DiagnosticsDialog opens and immediately begins running checks

#### Scenario: Dialog can be re-run
- **WHEN** the DiagnosticsDialog is already open and the user clicks "Re-run"
- **THEN** all check rows reset to pending state and the checks execute again from the beginning

---

### Requirement: Screen capture permission check
The system SHALL verify that screen capture is available on the current platform and report a clear pass or fail with a remediation hint when it fails.

#### Scenario: macOS — Screen Recording permission granted
- **WHEN** the diagnostics run on macOS and the application has Screen Recording permission
- **THEN** the screen capture check shows ✓ and the message "Screen Recording permission granted"

#### Scenario: macOS — Screen Recording permission denied
- **WHEN** the diagnostics run on macOS and the application does NOT have Screen Recording permission
- **THEN** the screen capture check shows ✗, the message "Screen Recording permission denied", and the hint "Open System Settings → Privacy & Security → Screen Recording and enable Drawing Coach"

#### Scenario: Linux — screen capture available
- **WHEN** the diagnostics run on Linux and `mss` can successfully grab monitor 0
- **THEN** the screen capture check shows ✓ and the message "Screen capture available"

#### Scenario: Linux — screen capture fails
- **WHEN** the diagnostics run on Linux and `mss` raises an exception when attempting to grab
- **THEN** the screen capture check shows ✗, the message includes the exception summary, and the hint "Ensure a display server (X11 or Wayland) is running and the app has display access"

#### Scenario: Windows — screen capture available
- **WHEN** the diagnostics run on Windows and `mss` can successfully grab monitor 0
- **THEN** the screen capture check shows ✓ and the message "Screen capture available"

---

### Requirement: Input Monitoring permission check (macOS only)
The system SHALL verify on macOS that the app has Input Monitoring permission so that global hotkeys function, reporting a clear pass or fail with a remediation hint when it fails. On non-macOS platforms this check SHALL be skipped (not shown as a row).

#### Scenario: macOS — Input Monitoring permission granted
- **WHEN** the diagnostics run on macOS and `AXIsProcessTrustedWithOptions` returns `True`
- **THEN** the Input Monitoring check shows ✓ and the message "Input Monitoring permission granted"

#### Scenario: macOS — Input Monitoring permission denied
- **WHEN** the diagnostics run on macOS and `AXIsProcessTrustedWithOptions` returns `False`
- **THEN** the Input Monitoring check shows ✗, the message "Input Monitoring permission denied", and the hint "Open System Settings → Privacy & Security → Input Monitoring and enable Drawing Coach; hotkeys will not work without this"

---

### Requirement: xdotool availability check (Linux only)
The system SHALL verify on Linux that `xdotool` is present in PATH, reporting a clear pass or fail with a remediation hint when it is missing. On non-Linux platforms this check SHALL be skipped.

#### Scenario: Linux — xdotool found
- **WHEN** the diagnostics run on Linux and `shutil.which("xdotool")` returns a path
- **THEN** the xdotool check shows ✓ and the message "xdotool found"

#### Scenario: Linux — xdotool not found
- **WHEN** the diagnostics run on Linux and `shutil.which("xdotool")` returns `None`
- **THEN** the xdotool check shows ✗, the message "xdotool not found", and the hint "Install xdotool (e.g. sudo apt install xdotool) — without it no drawing windows can be detected"

---

### Requirement: LLM connectivity check
The system SHALL verify that a model name is configured and that a minimal text completion call succeeds, reporting pass/fail with a remediation hint.

#### Scenario: LLM check passes
- **WHEN** diagnostics run, a model name is set in config, and `litellm.completion` returns a response
- **THEN** the LLM check shows ✓ and the message "LLM connection successful (text completion)"

#### Scenario: No model configured
- **WHEN** diagnostics run and the model name field in config is empty
- **THEN** the LLM check shows ✗, the message "No model configured", and the hint "Open Settings → LLM tab and enter a model name (e.g. gpt-4o or ollama/llava)"

#### Scenario: LLM call fails
- **WHEN** diagnostics run, a model name is set, but the `litellm.completion` call raises an exception
- **THEN** the LLM check shows ✗, the message includes the exception type and summary, and the hint "Check your API key, Base URL, and network connection in Settings → LLM"

---

### Requirement: Config file access and integrity check
The system SHALL verify that the config directory is writable so that settings can be saved, and that the existing config file (if present) contains valid JSON so settings are not silently lost.

#### Scenario: Config directory writable and file valid
- **WHEN** diagnostics run, the config directory is writable, and the config file either does not exist or contains valid JSON
- **THEN** the config check shows ✓ and the message includes the resolved config path

#### Scenario: Config directory not writable
- **WHEN** diagnostics run and the config directory exists but is not writable by the current user
- **THEN** the config check shows ✗ and the hint "Check file permissions on {config_dir} or run the app as a user with write access"

#### Scenario: Config file contains invalid JSON
- **WHEN** diagnostics run, the config directory is writable, but the config file exists and cannot be parsed as JSON
- **THEN** the config check shows ✗ and the hint "The config file at {config_path} is corrupt — delete it to reset to defaults"

---

### Requirement: Sessions directory access check
The system SHALL verify that the sessions data directory exists (or can be created) and is writable.

#### Scenario: Sessions directory writable
- **WHEN** diagnostics run and the sessions directory is writable (creating it if absent)
- **THEN** the sessions check shows ✓ and the message includes the resolved sessions path

#### Scenario: Sessions directory cannot be created or is not writable
- **WHEN** diagnostics run and the sessions directory either cannot be created or exists but is not writable
- **THEN** the sessions check shows ✗ and the hint "Check permissions on {sessions_dir_parent} or set XDG_DATA_HOME to a writable directory"

---

### Requirement: Pillow PNG codec check
The system SHALL verify that Pillow can encode PNG images, since captured frames are silently dropped when this codec is unavailable.

#### Scenario: Pillow PNG encoding works
- **WHEN** diagnostics run and `Image.new("RGB", (1, 1)).save(io.BytesIO(), "PNG")` succeeds
- **THEN** the Pillow check shows ✓ and the message "Pillow PNG codec available"

#### Scenario: Pillow PNG encoding fails
- **WHEN** diagnostics run and the above call raises an exception
- **THEN** the Pillow check shows ✗, the message includes the exception summary, and the hint "Reinstall Pillow: uv pip install --reinstall Pillow"

---

### Requirement: Progressive check display
The system SHALL display each check result as soon as it completes rather than waiting for all checks to finish.

#### Scenario: Checks appear incrementally
- **WHEN** the diagnostics are running and the LLM check (which can take several seconds) is in progress
- **THEN** already-completed checks above it are already showing their ✓ / ✗ status while the LLM row shows a spinner or "checking…" state

---

### Requirement: Checks run off the main thread
The system SHALL run all diagnostic checks in a background thread so the dialog remains interactive during execution.

#### Scenario: UI remains responsive during slow LLM check
- **WHEN** the LLM connectivity check is blocked waiting for a network response
- **THEN** the "Re-run" button and dialog close button remain clickable and responsive

