## 1. Frame selection fix

- [x] 1.1 In `src/drawing_coach/feedback_engine.py`, update `_build_messages` (or `request_feedback`) so that when `mode == "overlay"`, `selected = [frames[-1]]` regardless of `self._config.lookback_frames`
- [x] 1.2 Confirm other modes (`quick_hint`, `full_critique`, `practice_exercise`) still apply the existing `lookback_frames` selection logic unchanged

## 2. Label legibility

- [x] 2.1 In `src/drawing_coach/overlay_renderer.py`, add fixed, preselected module-level constants for label text color and label background color (e.g. black text on a white/light background) — no dynamic/luminance-based computation
- [x] 2.2 Before drawing arrow labels, compute the text bounding box via `draw.textbbox` (with small padding) and draw a filled background rectangle using the fixed background color, then draw the label text on top in the fixed text color (independent of the annotation's own `color`)
- [x] 2.3 Apply the same background-rectangle treatment to circle labels

## 3. Tests

- [x] 3.1 Add a test asserting that an overlay-mode request sends exactly one image regardless of `lookback_frames` (e.g. configured to 2 with 3+ frames available)
- [x] 3.2 Add/confirm a test asserting non-overlay modes still send `lookback_frames + 1` images (regression guard for existing behavior)
- [x] 3.3 Add a test covering `lookback_frames == 0` with `mode == "overlay"` still sends exactly one image (no change from current behavior, but guards the branch)
- [x] 3.4 Add a test asserting a label rendered on annotations of each of the supported `_COLOR_MAP` colors (including "white" and "black") always uses the same fixed text/background color pair, regardless of the annotation's own color
- [x] 3.5 Add a test asserting the background rectangle is sized to the label's actual text bounding box, not a fixed arbitrary size

## 4. Documentation

- [x] 4.1 Update README.md (developer-facing) to note that overlay mode always analyses a single frame, independent of the configured look-back setting, and that annotation labels always render with a contrasting background
- [x] 4.2 Update `.claude/CLAUDE.md` if it documents `FeedbackEngine`'s frame-selection behavior, to reflect the overlay-mode exception (no changes — CLAUDE.md doesn't document this behavior)
- [x] 4.3 Review `openspec/config.yaml` and propose changes only if this change reveals a clear, recurring gap in the current rules (high threshold — skip if nothing qualifies) (no changes — this is a narrow bug fix, not a recurring pattern)
- [x] 4.4 Run `uv run pytest` and confirm all tests pass
