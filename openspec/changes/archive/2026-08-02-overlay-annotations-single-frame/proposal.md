## Why

In overlay feedback mode, `FeedbackEngine` sends the latest frame plus up to `lookback_frames` (default 2) prior frames to the LLM so it can comment on how the drawing evolved. But the LLM's annotation coordinates are normalised 0–1 relative to *an* image, and nothing in the request tells it which of the several images sent that is — while the app always renders the returned annotations onto only the single most recent frame. When the canvas has scrolled or panned between captures, the LLM can describe content it saw in an earlier lookback frame (e.g. a head/face) that is no longer present in the latest frame, and those coordinates get stamped onto the wrong image. The result is nonsensical overlays: arrows and labels pointing at anatomy or features that don't appear anywhere in the frame being annotated. Separately, annotation label text is drawn directly onto the drawing with no background, so a label can become unreadable whenever its color is close to the color of the drawing content directly beneath it.

## What Changes

- When feedback mode is `overlay`, the request to the LLM SHALL include only the single most recent frame — `lookback_frames` is bypassed for this mode so there is no ambiguity about which image the returned coordinates describe.
- Other modes (`quick_hint`, `full_critique`, `practice_exercise`) are unaffected — they only produce prose, not pixel coordinates, so the existing lookback behavior is unchanged.
- Every annotation label (on `arrow` and `circle` types) SHALL be drawn with a background behind its text, sized to the text, using a fixed, preselected text/background color pair (independent of the annotation's own line/arrow color), so the label stays legible regardless of what's underneath it — no dynamic contrast computation.

## Capabilities

### Modified Capabilities
- `llm-feedback`: the "send screenshot + look-back frames" requirement gains a mode-specific exception — overlay mode always sends exactly one frame (the latest), regardless of the configured look-back count.
- `overlay-feedback`: adds a requirement that annotation coordinates are always rendered onto the same single frame that was sent to the LLM, eliminating the possibility of coordinates from a stale/different frame being drawn onto the current one; also adds a requirement that annotation label text always renders with a contrasting background.

## Impact

- `src/drawing_coach/feedback_engine.py`: `_build_messages` (or its caller) selects only `frames[-1]` when `mode == "overlay"`, instead of applying `lookback_frames` uniformly across all modes.
- `src/drawing_coach/main_window.py`: no behavioral change expected — `_trigger_feedback` already renders onto `frames[-1].image`; this proposal makes that assumption actually hold for the LLM's coordinate space too.
- `src/drawing_coach/overlay_renderer.py`: `_render_annotation` draws a contrasting background rectangle behind each label's text before drawing the text itself.
- Known, accepted trade-off: the history panel's lookback indicator (`lookback-indicator` capability) is not mode-aware and will continue to highlight `lookback_frames + 1` frames even when overlay mode is selected, which will now send only 1. Not addressed here — out of scope for this fix.
