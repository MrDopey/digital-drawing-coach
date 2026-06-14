## Why

New users frequently struggle to get Drawing Coach working because three distinct systems must all be configured correctly before coaching feedback can flow: OS-level screen capture permissions, a working LLM connection, and writable data directories. There is no single place to verify all of these at once, so failures surface as silent hangs or cryptic errors mid-session.

## What Changes

- Add a **"Run Diagnostics"** button to the Settings dialog (or main window toolbar) that runs a series of health checks in sequence and displays a pass/fail report
- Checks include:
  - **Screen capture permission** — on macOS, verifies the app has Screen Recording permission; on Linux/Windows, verifies `mss` can capture at least one monitor
  - **Input Monitoring permission** (macOS only) — verifies the app has Input Monitoring permission so global hotkeys work; failure is currently swallowed silently
  - **LLM connectivity** — verifies a model name is configured and that a test completion call succeeds (reuses existing logic from "Test Connection")
  - **Config file access** — verifies the config directory is writable (for saves) and that the existing config JSON is valid (malformed JSON silently resets all settings to defaults)
  - **Sessions directory** — verifies the sessions data directory exists (or can be created) and is writable
  - **xdotool available** (Linux only) — verifies `xdotool` is in PATH; without it the window picker silently shows "No windows found"
  - **Pillow PNG codec** — verifies Pillow can encode PNG images; without it captured frames are silently dropped and session history is never written to disk
- Each check shows a ✓ / ✗ status with a brief human-readable message and, on failure, an actionable hint (e.g. "Open System Settings → Privacy → Screen Recording")
- The diagnostic panel is non-modal and can be re-run without closing the window

## Capabilities

### New Capabilities
- `system-diagnostics`: A diagnostic panel that runs platform-aware health checks and surfaces pass/fail results with actionable remediation hints

### Modified Capabilities
- `llm-config`: Surface the existing LLM connectivity test as one check within the diagnostics panel (no requirement change, just reuse)

## Impact

- New module `drawing_coach/diagnostics.py` — platform-aware check functions and a `DiagnosticsDialog` PyQt6 widget
- `settings_dialog.py` — add a "Diagnostics…" button that opens the dialog
- `_backend_macos.py` — expose helpers for querying Screen Recording and Input Monitoring permission status
- No new dependencies; uses `mss`, `litellm`, `PyQt6`, `shutil`, `Pillow`, and stdlib `pathlib`/`os`/`json`
