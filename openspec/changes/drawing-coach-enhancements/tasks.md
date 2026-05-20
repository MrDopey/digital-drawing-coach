## 1. Config Schema Extensions

- [ ] 1.1 Add new fields to `config.json` schema: `lookback_frames` (default 2), `dedup_threshold` (default 2.0), `history_retention_sessions` (default 10), `stuck_consecutive_count` (default 3), `stuck_cooldown_minutes` (default 5), `style_focus` (default "")
- [ ] 1.2 Update `llm_config.py` to load, validate, and expose all new config fields with their defaults
- [ ] 1.3 Add new settings panel sections for Stuck Detection (MAE threshold, consecutive count, cooldown) and History (retention count, dedup threshold, look-back frames)

## 2. Disk-Backed Session History

- [ ] 2.1 Create session directory structure: `~/.drawing-coach/sessions/<session-id>/frames/` on session start
- [ ] 2.2 Write `meta.json` per session with `{drawing_app, style_focus, start_time}`
- [ ] 2.3 Rewrite `capture_engine.py` storage layer to write accepted frames as PNG to session `frames/` directory immediately on capture
- [ ] 2.4 On startup, load the most recent session from disk if it started within the last 24 hours; otherwise start a new session directory
- [ ] 2.5 Implement session cleanup on startup: delete oldest session directories until only `history_retention_sessions` remain
- [ ] 2.6 Apply cleanup immediately when user lowers retention limit in settings and saves

## 3. Duplicate Frame Detection

- [ ] 3.1 Add `dedup_threshold` check in `capture_engine.py` before writing each frame: compute MAE against last stored frame; drop if below threshold
- [ ] 3.2 Ensure dedup uses a separate threshold from stuck-detection MAE (read `dedup_threshold` from config)
- [ ] 3.3 Add unit tests for dedup logic: identical frames dropped, distinct frames accepted, threshold boundary cases

## 4. Configurable Stuck Detection Parameters

- [ ] 4.1 Replace hardcoded constants in `stuck_detector.py` with config reads for `stuck_threshold`, `stuck_consecutive_count`, and `stuck_cooldown_minutes`
- [ ] 4.2 Hot-reload all three parameters when user saves settings (no session restart required)
- [ ] 4.3 Update settings panel Stuck Detection section with three input fields and their default values displayed as placeholders

## 5. Configurable Look-Back Frame Count

- [ ] 5.1 Update `feedback_engine.py` to read `lookback_frames` from config instead of hardcoded 2
- [ ] 5.2 Clamp look-back to number of available stored frames (no error if fewer frames exist)
- [ ] 5.3 Handle `lookback_frames = 0`: send only current screenshot with no history

## 6. Drawing Style / Focus

- [ ] 6.1 Add style selector widget to main UI: dropdown with presets (Line Drawing, Realistic, Anime/Manga, Chibi, Concept Art, Portrait) plus free-text input field below it
- [ ] 6.2 Implement mutual exclusion: selecting a preset clears free-text; entering free-text deselects preset
- [ ] 6.3 Display active style/focus as "Coaching for: <value>" label in main window; show "General" when nothing set
- [ ] 6.4 Persist selected style/focus to `config.json` on change; load on startup
- [ ] 6.5 Inject style/focus into LLM system prompt in `feedback_engine.py`: "The user is currently practising: <style>" (preset) or "The user is currently focusing on: <text>" (free-text)
- [ ] 6.6 Enforce 200-character max on free-text input with truncation warning

## 7. Expanded LLM Error Handling

- [ ] 7.1 Extend `feedback_engine.py` error handler to catch `litellm.RateLimitError` → "Rate limit reached — wait a moment and try again"
- [ ] 7.2 Catch `litellm.InsufficientQuotaError` / `litellm.BudgetExceededError` → "Your API credits are exhausted — top up your account to continue"
- [ ] 7.3 Catch `litellm.NotFoundError` → "Model not found — check the model name in your LLM settings"
- [ ] 7.4 After successful LLM response, check response body for policy-refusal phrases ("I'm unable to", "I cannot assist", "content policy"); if matched, show "The LLM flagged a content policy issue — try a different feedback mode or drawing" and do not render as feedback
- [ ] 7.5 Write unit tests covering each error type with mocked LiteLLM exceptions

## 8. Overlay Feedback Mode

- [ ] 8.1 Write overlay system prompt template instructing LLM to return a JSON annotation block with `annotations` array (types: `arrow`, `line`, `circle`) using normalised 0–1 coordinates
- [ ] 8.2 Implement `overlay_renderer.py`: parse annotation JSON from LLM response text, composite annotations onto a Pillow copy of the screenshot
- [ ] 8.3 Implement `arrow` rendering: draw line + arrowhead polygon + optional label text near tip
- [ ] 8.4 Implement `line` rendering: draw polyline through normalised points in specified colour
- [ ] 8.5 Implement `circle` rendering: draw circle outline at normalised center/radius + optional label above
- [ ] 8.6 Implement graceful fallback: if JSON parse fails, display text response + "Visual overlay unavailable — showing text feedback instead"
- [ ] 8.7 Add "Overlay" as fourth option in the feedback mode selector in the main UI
- [ ] 8.8 Display composited annotated image in the feedback panel alongside the explanatory text
- [ ] 8.9 Add "Save Overlay" button to feedback panel: opens file dialog and saves composited PNG
- [ ] 8.10 Write unit tests for annotation rendering (arrow, line, circle) with synthetic annotation JSON

## 9. Integration & Verification

- [ ] 9.1 End-to-end test: select a style, trigger feedback, verify style appears in LLM request system prompt
- [ ] 9.2 End-to-end test: run capture for multiple intervals with identical screenshots, verify no duplicates written to disk
- [ ] 9.3 End-to-end test: set retention to 2, create 3 sessions, restart app, verify oldest session deleted
- [ ] 9.4 End-to-end test: select Overlay mode, trigger feedback with mocked LLM returning annotation JSON, verify rendered image displayed
- [ ] 9.5 End-to-end test: mock rate-limit error from LiteLLM, verify correct user-facing message shown
