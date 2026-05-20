## Why

The initial digital-drawing-coach design covers the core coaching loop but leaves several gaps that limit its usefulness: feedback is text-only with no visual annotation, the LLM has no knowledge of what style the user is practising, session history is volatile (lost on restart), and key detection/history parameters are hardcoded rather than user-configurable. These additions make the coach more contextually aware, more resilient, and more flexible for different learning goals.

## What Changes

- **New**: Overlay feedback mode — the LLM returns correction lines/marks that are composited directly onto the drawing screenshot and displayed to the user
- **New**: Drawing style & focus selector — a preconfigured list (line drawing, realistic, anime/manga, chibi, concept art, portrait) plus free-text input; the selected style/focus is injected into every LLM prompt
- **Modified**: `feedback-modes` gains the new overlay mode as a fourth option
- **Modified**: `llm-feedback` surfaces all LLM error categories — copyright flags, rate-limit responses, and credit-exhaustion errors — in addition to existing auth and network errors
- **Modified**: `screenshot-capture` — session history is persisted to disk; duplicate/near-duplicate frames are dropped before storage; look-back frame count is configurable; history auto-cleans to retain only the last X sessions (configurable)
- **Modified**: `stuck-detection` — all inactivity detection parameters (pixel-change threshold, consecutive interval count, cooldown duration) are fully config-driven with sensible defaults

## Capabilities

### New Capabilities

- `overlay-feedback`: LLM-generated visual annotations (correction strokes, arrows, labels) are rendered on top of the drawing screenshot and presented as an annotated image in the feedback panel
- `drawing-style-focus`: User selects their current drawing style from a preset list or enters free text; this context is included in every LLM system prompt to focus coaching on style-appropriate criteria

### Modified Capabilities

- `feedback-modes`: adding overlay as a fourth feedback mode alongside Quick Hint, Full Critique, and Practice Exercise
- `llm-feedback`: adding copyright flag, rate-limit, and credit-exhaustion error surfaces; making look-back frame count configurable rather than fixed at 2
- `screenshot-capture`: replacing in-memory ring buffer with disk-backed session history; adding duplicate-frame detection and drop; adding configurable look-back count; adding configurable history retention (last X sessions)
- `stuck-detection`: all three inactivity parameters (MAE threshold, consecutive interval count, cooldown) move from hardcoded defaults to user-configurable settings persisted in the config file

## Impact

- `capture_engine.py` — rewrite storage layer to write frames to disk under a session directory; add MAE-based duplicate filter before write; add session cleanup job
- `stuck_detector.py` — read threshold, consecutive count, and cooldown from config instead of constants
- `feedback_engine.py` — extend error handling for copyright/rate-limit/credit errors; make look-back frame count a config value; add overlay rendering pipeline (Pillow compositing)
- `feedback_modes.py` / UI — add overlay mode option and render annotated image output
- `llm_config.py` + settings panel — add fields: history retention count, look-back frame count, stuck-detection parameters, drawing style/focus
- New dependency: none beyond existing Pillow (already required); LLM overlay output will use SVG/JSON coordinate format parsed and drawn with Pillow
