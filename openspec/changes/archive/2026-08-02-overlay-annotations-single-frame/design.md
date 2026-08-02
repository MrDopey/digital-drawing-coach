## Context

`FeedbackEngine._build_messages` (`src/drawing_coach/feedback_engine.py:187-217`) applies the same frame-selection logic to every feedback mode:

```python
lookback = max(0, self._config.lookback_frames)
if lookback == 0:
    selected = [frames[-1]]
else:
    selected = frames[-(lookback + 1):]
```

`lookback_frames` defaults to 2 (`llm_config.py:19`), so a typical request sends 3 chronologically-ordered images with `[filename]` text markers before each. This is correct and desired for the prose modes (`quick_hint`, `full_critique`, `practice_exercise`) — the system prompt explicitly asks the LLM to "comment on how the work has evolved" across them.

`overlay` mode reuses the exact same selection call, but its response isn't prose — it's a JSON `annotations` array of coordinates normalised 0–1 "relative to image width/height" (`_MODE_TEMPLATES["overlay"]`, line 62). The prompt never says *which* of the (possibly 3) images those coordinates are relative to. Separately, `MainWindow._trigger_feedback` (`main_window.py:559-560`) always renders the returned annotations onto `latest_image = frames[-1].image` — captured once, before the LLM call, and passed straight into `render_overlay`.

When the drawing canvas is scrolled or panned between captures (a common case — e.g. drawing a head, then scrolling down to work on the torso), an older lookback frame can contain content (a face) that the latest frame no longer shows. The LLM, seeing all 3 images, may anchor its annotations to that older frame's content. Those coordinates then get drawn onto the latest frame in `render_overlay`, producing annotations for anatomy that isn't present anywhere in the image being annotated — arrows and labels floating over blank canvas or unrelated content.

Separately, `overlay_renderer._render_annotation` (`src/drawing_coach/overlay_renderer.py:58-60` for `arrow`, `:74-76` for `circle`) draws label text directly onto the image with `draw.text(pos, label, fill=color)` and no backing of any kind. Whenever the label's color is close to the color of the drawing content directly beneath it — e.g. red label text over red-ish pencil strokes, or white label text over blank white canvas — the label becomes unreadable. This is independent of the frame-mismatch bug above and can occur even when the annotation is correctly placed on the right frame.

## Goals / Non-Goals

**Goals:**
- Guarantee that in overlay mode, the frame the LLM annotates and the frame the app renders annotations onto are always the same single image, eliminating any possibility of cross-frame coordinate mismatch.
- Leave prose-mode behavior (frame selection, multi-image progression commentary) completely unchanged.
- Guarantee annotation label text remains legible regardless of what's drawn underneath it, using a fixed, preselected text/background color pair rather than per-annotation dynamic contrast computation.

**Non-Goals:**
- Not making the LLM aware of multiple frames' worth of history for overlay mode — overlay mode's job is "correct this specific drawing," not "comment on progression," so losing lookback context there is acceptable and arguably more focused.
- Not changing the `lookback_frames` config value, its UI, or its semantics for other modes.
- Not making the history panel's lookback indicator (`lookback-indicator` capability) mode-aware. It will keep showing `lookback_frames + 1` highlighted frames regardless of which mode is currently selected in the feedback panel, which is now only accurate for the prose modes. Fixing that would require threading the selected mode from `FeedbackPanel` into `HistoryPanel` at dialog-open time; deferred as a separate, purely cosmetic follow-up.
- Not adding any indication to the LLM prompt of multiple frames for overlay mode — sending one frame removes the ambiguity structurally, so no prompt-engineering workaround (e.g. "use the LAST image only") is needed or attempted.

## Decisions

**Decision: In `FeedbackEngine._build_messages`, when `mode == "overlay"`, select only `[frames[-1]]`, bypassing `lookback_frames` entirely for that call.**

- Alternative considered: keep sending all lookback frames to the LLM, but add an explicit prompt instruction telling it annotation coordinates must be relative to the *last* image only. Rejected — this relies on the model correctly following an instruction under multi-image input, which is exactly the kind of soft constraint that produced the original bug (the existing prompt already implies single-image coordinates and the model still drifted). A structural fix (physically not sending the other images) removes the failure mode instead of hoping the model honors a rule.
- Alternative considered: keep sending all lookback frames, but have `render_overlay` accept multiple candidate images and let annotation entries specify which frame index they refer to. Rejected — this requires changing the LLM response schema (breaking any saved/cached annotation JSON and the `overlay-feedback` spec's documented annotation format) for a problem that's fully solved by simply not sending extra images in this mode.
- This decision alone requires no change to `render_overlay` or `overlay_renderer.py` — see the label-background decision below for the one change that does touch that file.

**Decision: Leave `lookback_frames` config and the lookback indicator as-is; do not thread the current mode into `HistoryPanel`.**

- The indicator becoming slightly inaccurate for one of four modes is a minor, purely cosmetic inconsistency (it will show extra highlighted frames that overlay mode won't actually use), not a functional bug — no wrong data is displayed, just an overly generous highlight. Fixing it requires new plumbing (passing the active mode from `FeedbackPanel` to `HistoryPanel` at dialog-open time, and updating `_update_lookback_indicator` to branch on it) that's disproportionate to the cosmetic issue and orthogonal to fixing the actual annotation-mismatch bug.

**Decision: In `overlay_renderer._render_annotation`, before drawing arrow/circle label text, draw a filled background rectangle sized to the label's text bounding box (`draw.textbbox`, with small padding), using a fixed, preselected label text color and background color — always the same pair, independent of the annotation's own line/arrow color.**

- The label text color and background color are module-level constants (e.g. black text on a white/light background), chosen once for guaranteed contrast against arbitrary drawing content. The annotation's own `color` field continues to control the arrow/line/circle stroke only, not the label text.
- Alternative considered: choose the background dynamically via a luminance check against the label's own text color (light text → dark backing, dark text → light backing). Rejected per explicit direction to avoid dynamic behavior — a single fixed pair is simpler to implement, test, and reason about, and still guarantees contrast against any drawing content since the pair itself is a fixed high-contrast combination.
- Alternative considered: draw a stroke/halo effect around the text glyphs instead of a filled rectangle. Rejected — Pillow's `ImageDraw` has no native text-stroke primitive, and a filled rectangle is simpler, cheaper, and guarantees full contrast rather than a thin halo that can still wash out against a similar background.
- Scoped entirely to `overlay_renderer.py`: no change to `render()`'s function signature, the annotation JSON schema, or any caller (`main_window.py`).

## Risks / Trade-offs

- [Overlay mode loses any progression context across frames, so LLM feedback text in overlay mode can no longer reference "compared to your last capture..."] → Acceptable: overlay mode's stated purpose is corrective annotation on the current drawing, not progression commentary; that's still available via `full_critique`/`quick_hint`.
- [History panel's lookback indicator over-highlights relative to what overlay mode actually sends] → Documented as an accepted, non-blocking cosmetic inconsistency (see Non-Goals); not fixed by this change.
- [Existing tests may assert `_build_messages` sends `lookback_frames + 1` images regardless of mode] → Update/add tests covering `mode == "overlay"` specifically sending exactly one image, and confirm other modes' existing tests still pass unchanged.
- [A fixed label text/background pair may look visually harsh or clash next to colored annotation lines] → Acceptable trade-off — guaranteed legibility takes priority over aesthetic polish for a coaching overlay, and a fixed pair is simpler and more predictable than per-annotation color matching.

## Migration Plan

No data migration; this is a pure behavior fix in request construction and rendering.
1. Change `FeedbackEngine._build_messages` (or `request_feedback`, whichever is the cleaner seam) to select only `frames[-1]` when `mode == "overlay"`.
2. Add fixed, preselected label text/background color constants to `overlay_renderer.py` and apply the background rectangle to both arrow and circle label rendering.
3. Add/update unit tests asserting: overlay mode sends exactly 1 image regardless of `lookback_frames`; other modes are unaffected; every label gets a background rectangle using the fixed color pair, sized to its text.
4. Ship as a normal patch — no feature flag needed, both were strictly bugs (annotations that don't match the annotated image; labels that can be unreadable).
5. Rollback: revert the commit; behavior returns to sending `lookback_frames + 1` images for all modes including overlay, and labels are drawn with no background.
