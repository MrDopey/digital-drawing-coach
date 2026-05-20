## 1. Project Setup

- [ ] 1.1 Create Python project structure with `src/` layout and `pyproject.toml`
- [ ] 1.2 Add dependencies: `mss`, `Pillow`, `numpy`, `pynput`, `litellm`, `PyQt6`, `keyring`
- [ ] 1.3 Add platform-conditional dependencies: `pywin32` (Windows), `pyobjc` (macOS)
- [ ] 1.4 Create entry point script and verify app launches to a blank window

## 2. Window Manager (App Selection)

- [ ] 2.1 Implement `window_manager.py` abstraction with `list_windows()` and `get_window_rect(window_id)` interface
- [ ] 2.2 Implement Windows backend using `pywin32` (`win32gui.EnumWindows`)
- [ ] 2.3 Implement macOS backend using `pyobjc` (`Quartz.CGWindowListCopyWindowInfo`)
- [ ] 2.4 Implement Linux/X11 backend using `xlib` or `subprocess xdotool`
- [ ] 2.5 Build app selection dialog: window list with thumbnails, refresh button, confirm selection
- [ ] 2.6 Handle "selected window closed" event — pause capture and show reselect prompt

## 3. Screenshot Capture

- [ ] 3.1 Implement `capture_engine.py` with `mss`-based window screenshot using bounding rect from window manager
- [ ] 3.2 Implement ring buffer (`collections.deque(maxlen=20)`) for captured frames with timestamps
- [ ] 3.3 Implement configurable capture interval timer (default 30s, range 5–300s)
- [ ] 3.4 Add pause/resume control and status indicator in main UI
- [ ] 3.5 Build session history panel showing thumbnails in chronological order with timestamps
- [ ] 3.6 Wire capture interval setting to timer without restarting session

## 4. Stuck Detection

- [ ] 4.1 Implement `stuck_detector.py` with MAE pixel comparison using `numpy`
- [ ] 4.2 Add configurable threshold and consecutive-interval count settings
- [ ] 4.3 Implement cooldown timer (default 5 min) that blocks re-trigger until elapsed
- [ ] 4.4 Register global hotkey using `pynput` for manual feedback trigger
- [ ] 4.5 Expose hotkey configuration in settings with conflict warning logic
- [ ] 4.6 Ensure manual hotkey trigger bypasses cooldown and resets the timer

## 5. LLM Configuration

- [ ] 5.1 Create `llm_config.py` with model name, API key (via `keyring`), and base URL fields
- [ ] 5.2 Build settings panel UI with form fields, Save button, and Test Connection button
- [ ] 5.3 Implement "Test Connection" — send minimal prompt and display success or error
- [ ] 5.4 Implement config export (JSON without API key) and import (populate fields, prompt for key)
- [ ] 5.5 Validate config completeness before allowing feedback requests; show setup prompt if missing

## 6. LLM Feedback Engine

- [ ] 6.1 Implement `feedback_engine.py` with art-coaching system prompt constant
- [ ] 6.2 Build `LiteLLM` call: encode screenshot(s) as base64, construct messages array, call `litellm.completion()`
- [ ] 6.3 Include up to 2 prior history frames alongside the current screenshot in the request
- [ ] 6.4 Implement request rate-limiting (ignore requests within 10 seconds of previous)
- [ ] 6.5 Surface LLM error types (auth, network, model-not-found) as user-friendly messages
- [ ] 6.6 Append user custom instructions to system prompt when configured

## 7. Feedback Modes

- [ ] 7.1 Implement three prompt templates: Quick Hint, Full Critique, Practice Exercise
- [ ] 7.2 Add mode selector (radio buttons or dropdown) in main UI; persist selection in session state
- [ ] 7.3 Inject selected mode template into system prompt before each LLM call
- [ ] 7.4 Build feedback panel: floating, draggable window with markdown rendering and dismiss button
- [ ] 7.5 Implement session feedback history: store all responses with timestamp and mode; add "Previous Feedback" button

## 8. Integration & Polish

- [ ] 8.1 Wire all components: app selection → capture → stuck detection → feedback engine → feedback panel
- [ ] 8.2 Add system tray icon with quick-access menu (pause/resume, trigger feedback, open settings, quit)
- [ ] 8.3 Implement first-run onboarding flow: configure LLM → select drawing window → enable capture
- [ ] 8.4 Add macOS screen recording permission check at startup with link to System Settings
- [ ] 8.5 Write README with setup instructions, dependency install steps, and LiteLLM config examples

## 9. Testing

- [ ] 9.1 Unit tests for `stuck_detector.py` MAE logic with synthetic image pairs
- [ ] 9.2 Unit tests for `capture_engine.py` ring buffer behavior (overflow, timestamps)
- [ ] 9.3 Unit tests for `llm_config.py` validation and export/import round-trip
- [ ] 9.4 Integration test for `feedback_engine.py` using a mocked LiteLLM response
- [ ] 9.5 Manual end-to-end test: select Paint/Krita window, let capture run, trigger feedback via hotkey, verify response displays
