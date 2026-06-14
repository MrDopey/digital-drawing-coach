## Why

Coaching feedback disappears when the app restarts — there is no record of what the LLM said in previous sessions. The current Get Feedback popup also has no sidebar for navigating history, no thumbnail showing which drawing the feedback referred to, and no guard against re-submitting the same images for the same mode.

## What Changes

- Each `FeedbackResponse` is saved to disk as `feedback/<session-id>/YYYYMMDD_HHMMSS_<mode>.json` when it arrives, including image hashes (SHA-256), the feedback text, annotation JSON (if overlay mode), and a small thumbnail of the last frame sent
- The saved history for the current session is loaded on startup so previous entries are immediately available
- The **Generate Feedback** button is disabled when the current frame hashes + selected mode match the last matching saved entry; re-enabled when a new frame arrives or the mode changes
- The Get Feedback popup is redesigned:
  - **Top row**: feedback type selector + Generate Feedback button (with disabled state)
  - **Left sidebar**: scrollable reverse-chronological list of all entries labelled `DD Mon  HH:MM: <mode>` (e.g. `14 Jun  09:41: Quick Look`); clicking jumps to that entry
  - **Main content area**: small thumbnail of the last image used (click opens in default viewer via `QDesktopServices`), feedback text (selectable, scrollable)
  - **Previous / Next** buttons for sequential navigation (preserved from current behaviour)

## Capabilities

### New Capabilities
- `feedback-persistence`: Save each `FeedbackResponse` (text, mode, timestamp, image hashes, thumbnail) to disk and load the session's history on startup
- `feedback-deduplication`: Disable Generate when current frames + mode already submitted; re-enable on change
- `feedback-panel-redesign`: Redesigned popup with sidebar history list, thumbnail preview, and top-row controls

### Modified Capabilities
- `llm-feedback`: `FeedbackEngine.request_feedback` must record the frame hashes it used alongside the response so the persistence layer can store and compare them

## Impact

- `src/drawing_coach/feedback_engine.py` — `FeedbackResponse` gains `frame_hashes: list[str]`; engine passes hashes through to the response
- `src/drawing_coach/feedback_panel.py` — full UI redesign; loads/saves history via new `FeedbackStore`
- New `src/drawing_coach/feedback_store.py` — disk persistence (save, load, thumbnail) for `FeedbackResponse`
- `src/drawing_coach/paths.py` — new `feedback_dir(session_id)` helper
- No new third-party dependencies (hashlib and json are stdlib; Pillow already present for thumbnails)
