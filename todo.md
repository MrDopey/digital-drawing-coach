bounding box issues with the overlay feedback
claude --resume c7ad2c9e-cec4-4766-8678-972a2bea9cc9

## overlay feedback bug — findings so far

Root cause isn't a single coordinate bug in `overlay_renderer.py` — the render
pipeline (image sent to the LLM == image rendered on, same dimensions, same
`w,h` scaling) is internally consistent. The problem is what the LLM's
normalised `[0,1]` coordinates actually turn out to mean vs. what the app
assumes (full captured window, chrome included).

Tested against one real debug sample
(`.tmp/20260803T000639576580_feedback_overlay_structured/`) under 6
hypotheses for what the coordinates might be relative to:
- **H0 full image (current app behavior)** — annotations land badly wrong:
  oversized head circle floating above/left of the actual head, hand/thumb
  arrows pointing at blank canvas.
- **H1 canvas-relative** (normalised to the detected white canvas rect,
  ignoring browser/app chrome) — head/face annotations line up dramatically
  better.
- **H5 character-bounding-box-relative** (normalised to a tight box around
  just the figure, excluding unrelated doodles elsewhere on the canvas) —
  even better fit than H1 for head/face.
- **Hand/thumb/clavicle annotations stay wrong under every single
  hypothesis**, including H5. That's not a coordinate-frame problem — the
  model just doesn't know where the hands are in that drawing. Cropping/
  reframing won't fix that class of error.

So there are plausibly two distinct bugs bundled into one symptom: a
systematic frame-of-reference mismatch (fixable) and a separate vision
grounding failure specific to hands (not fixable by remapping coordinates).
**Only tested on one sample so far** — needs repeating across more captures
before concluding H1/H5 generalize.

### Tooling built to keep investigating (not yet a production fix)

- `src/drawing_coach/overlay_debug_lib.py` — pure, tested logic: canvas
  auto-detection (light/white background heuristic) + `compute_hypotheses()`
  re-projecting one annotation set under H0-H5.
- `src/drawing_coach/overlay_debug_runner.py` — shared LLM-calling logic
  (editable system prompt, editable `response_format` schema, optional
  character bbox), used by both front-ends below.
- `scripts/overlay_debug_tool.py` — local web app (`uv run python
  scripts/overlay_debug_tool.py`): pick an image, edit the prompt/schema,
  drag a box around the character, Run, then toggle H0-H5 on/off over the
  image (SVG overlay + numbered badges + legend), see the raw LLM response
  pretty-printed, plus a pixel/percent grid overlay to sanity-check the
  render pipeline itself independent of any LLM call.
- `scripts/overlay_debug_cli.py` — headless version of the same thing, for
  scripted/agent-driven iteration: `--dump-defaults DIR` writes the current
  prod prompt+schema to edit, then `--prompt-file`/`--schema-file`/
  `--character-bbox` re-runs against an image. Exit code is the signal to
  act on: `0` clean parse, `1` got a response but it didn't parse (revise
  prompt/schema), `2` couldn't complete the request at all (config/image/
  network problem, unrelated to prompt wording).

### Not done yet

- No production code (`overlay_renderer.py`, `feedback_engine.py`) has been
  changed — everything above is diagnostic tooling only.
- Haven't decided *what* the production fix should be (crop capture to
  canvas before sending? tell the model the canvas bbox explicitly? something
  else?) — that decision should wait until H1/H5 are confirmed across more
  than one sample image.
- Hand-grounding failure is a separate, harder problem — unclear yet whether
  it's fixable at all via prompting/coordinates, or is just a model
  limitation on this kind of content.


ministral-14b-2512
