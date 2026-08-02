## Why

Coaching feedback disappears when the app restarts — there is no record of what the LLM said in previous sessions. The Feedback Management panel also has no way to browse that history other than one-at-a-time Previous/Next, no thumbnail showing which drawing non-overlay feedback referred to, and no guard against re-submitting the same images for the same mode.

## What Changes

- `FeedbackResponse` (already carrying `mode`, `text`, `timestamp`, `annotation_json`, `observations`, and `used_structured_output` from the structured-JSON-output-fallback change) gains a `frame_hashes: list[str]` field — the SHA-256 hex digest of each frame actually sent to the LLM, in send order.
- Each `FeedbackResponse` is saved to disk as `feedback/<session-id>/YYYYMMDD_HHMMSS_<mode>.json` when it arrives, round-tripping all of the fields above. A 160×120 JPEG thumbnail of the last frame sent is saved alongside. For overlay-mode entries, the composited annotated image is *also* saved (`..._overlay.png`) so the existing zoomable/pannable/saveable overlay view keeps working for reloaded history, not just the entry just generated.
- The current session's saved history is loaded into the panel on startup, and reloaded whenever the active session changes (New Session, or switching sessions via the Sessions menu) — the panel must never keep showing a previous session's history after a switch.
- The existing **Request Feedback** button (label unchanged — already locked in by the `feedback-modes` spec) is disabled when the current frame hashes + selected mode match the last saved entry for that mode; a tooltip explains why. It re-enables when a new frame arrives or the mode changes.
- The Feedback Management panel's existing top row (mode radio strip + Request Feedback button) and existing vertical splitter (zoomable annotated-overlay image on top, feedback text below) are wrapped in a new layout, not rebuilt:
  - **New left sidebar**: fixed-width (~180px), scrollable, reverse-chronological list of all entries labelled `DD Mon  HH:MM: <mode>` (e.g. `14 Jun  09:41: Quick Hint`); clicking a row jumps to that entry and stays in sync with Previous/Next.
  - **Overlay-mode entries** keep showing the existing full-size zoomable/pannable annotated image — unchanged behavior, now also restorable after a restart.
  - **Non-overlay entries** (Quick Hint, Full Critique, Practice Exercise — which currently show no image at all) gain a small thumbnail of the last frame sent; clicking it opens the image in the system default viewer via `QDesktopServices`, the same pattern already used in `history_panel.py`.
  - Resize behavior: the sidebar has a fixed width and does not stretch; the existing vertical splitter's panes and stretch factors are unchanged; the new thumbnail sits in the space the image pane already occupies when not showing an overlay image, so no new scroll area is needed beyond what already exists.
- The sidebar rows and thumbnail widget are built from `design_system.py` components (e.g. `MutedLabel`) and `theme.py` tokens, since `tests/test_design_system_compliance.py` now fails the build on raw `setStyleSheet()` calls or hex literals outside those two files.

## Capabilities

### New Capabilities
- `feedback-persistence`: Save each `FeedbackResponse` (all current fields, plus a thumbnail and, for overlay mode, the composited image) to disk; load the active session's history on startup and whenever the active session changes
- `feedback-deduplication`: Disable Request Feedback when current frames + mode already submitted; re-enable on change
- `feedback-panel-redesign`: Sidebar history list and mode-appropriate image preview (full zoomable overlay image, or small thumbnail), layered onto the panel's existing top row and splitter

### Modified Capabilities
- `llm-feedback`: `FeedbackEngine` must record the frame hashes it used alongside the response so the persistence layer can store and compare them (this modification preserves the already-merged overlay-single-frame requirement — it only adds `frame_hashes` on top)

### Known gap (not covered by this change)
- `feedback-modes`' existing "Feedback history is accessible within the session" requirement still describes a "Previous Feedback" list button that doesn't match either current code or this change's new sidebar. Reconciling that main-spec requirement with the sidebar (via a `feedback-modes` delta spec) is left for a follow-up pass, since this change's planning artifacts can't introduce a new delta-spec file for a capability none of them currently touch.

## Impact

- `src/drawing_coach/feedback_engine.py` — `FeedbackResponse` gains `frame_hashes: list[str]`; both the structured and prose request paths attach it
- `src/drawing_coach/feedback_panel.py` — sidebar and mode-appropriate image preview layered onto the existing mode row / vertical splitter / Prev-Next controls; gains a `set_store()` method to (re)bind and reload history
- New `src/drawing_coach/feedback_store.py` — disk persistence (save, load, thumbnail, overlay-image) for `FeedbackResponse`
- `src/drawing_coach/paths.py` — new `feedback_dir(session_dir: Path)` helper
- `src/drawing_coach/main_window.py` — constructs/rebinds the `FeedbackStore` via `feedback_panel.set_store()` after the session directory resolves at startup, and again in `_switch_session()` and `_new_session()`
- No new third-party dependencies (hashlib and json are stdlib; Pillow already present for thumbnails)
