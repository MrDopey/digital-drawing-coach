## Why

The coach gives the same generic advice every session because it has no memory of past observations — it cannot say "you've struggled with perspective across four sessions" or adjust its tone for a returning student vs. a first-time user. Feedback quality improves substantially when the LLM has structured context about the user's recurring patterns.

## What Changes

### Persisted memory: raw observations + a re-summarisation history

Two closely related, colocated features form the data layer:

- A `memory.json` file is maintained in the app data directory across sessions, storing a list of raw observations (each with `date`, `session_id`, `category`, `note`), appended after each feedback response. Total observations are capped at a configurable maximum (`memory_max_observations`, default 200; oldest pruned on overflow)
- Raw observations, left unchecked, would grow unbounded, so they are periodically condensed: a config setting, `memory_resummarize_interval` (default `20`), controls the cadence — every N appended observations, an LLM call condenses the accumulated raw notes into a compact block. Setting it to `0` opts out entirely and keeps notes raw forever
- Each condensation pass is **appended** (never overwriting the previous one) to a second file, `memory_summaries.json`, as its own entry in a re-summarisation history — this keeps a record of how the coach's understanding evolved over time. This history has its own cap, `memory_summary_history_max` (default 200; oldest pruned on overflow), independent of the observation cap, since the two lists grow at very different rates and serve different purposes (detailed raw record vs. condensed audit trail)

### How this feeds the LLM's advice

This is the reason the data layer above exists: before every LLM feedback request, `MemoryStore` produces a "coach's notes" block from that persisted memory — the *most recent* summary (if any) plus any raw observations appended since — and that block is what actually shapes the advice the LLM gives (e.g. "you've struggled with perspective across four sessions," or a calmer tone for a first-time user). Concretely:

- The coach's notes block is appended to the *end* of the system prompt, after the base persona/style/custom-instructions (which stay a stable, unchanging prefix), so LLM providers can still cache that prefix across requests instead of invalidating the cache every time memory changes
- The block also includes the total session count, derived from `sessions_dir()` (e.g. "You have worked with this student across 5 sessions.") — factual context alongside the notes, not paired with any explicit instruction telling the LLM what to do with it
- Keeping the injected block based on a single condensed summary (rather than raw notes growing forever, or concatenating the whole re-summarisation history) keeps it compact and high-signal on every request, so advice quality doesn't degrade as the store grows

### Settings and UI

- **Every config field this change introduces is user-editable from the Settings dialog** (new "Memory" tab: re-summarisation interval, observation cap, summary-history cap) — no field requires hand-editing `config.json`
- **Memory viewer**: reverse-chronological list grouped by category; per-row delete; clear-all with confirmation dialog (clears both `memory.json` and `memory_summaries.json`); export copies both files to a user-chosen location
- **Progress panel / tab**: summarises recurring themes (e.g. "Perspective mentioned 7 times across 4 sessions") and shows a simple timeline of session dates

## Capabilities

### New Capabilities
- `memory-store`: Persist observations to `memory.json` and re-summarisation history to `memory_summaries.json`; append, cap, prune, load each independently, and (on a configurable interval) re-summarise raw notes via an LLM call, appending each condensation to the separately-capped summary history
- `memory-context`: Format observations into a "coach's notes" block and append it to the end of the LLM system prompt before each request, preserving prompt-cache hits on the static prefix
- `memory-viewer`: UI to view, delete, clear, and export stored observations and summary history
- `progress-panel`: UI tab/panel summarising recurring themes and session frequency timeline

### Modified Capabilities
- `llm-feedback`: `FeedbackEngine._build_system_prompt` must accept and append (not prepend) an optional coach's notes block supplied by the memory layer, after the mode template, so the static persona/style/custom-instructions prefix is unaffected

## Impact

Data layer (persisted memory):
- New `src/drawing_coach/memory_store.py` — `MemoryStore`: loads/saves `memory.json` (observations) and `memory_summaries.json` (summary history) independently; append, prune, and cap each; summarise (raw formatting + periodic LLM re-summarisation appended to the summary history)
- `src/drawing_coach/paths.py` — new `memory_path() -> Path` and `memory_summaries_path() -> Path` helpers
- `src/drawing_coach/llm_config.py` — new `memory_resummarize_interval: int = 20` config field (re-summarises every N appended responses; `0` opts out and keeps notes raw), new `memory_max_observations: int = 200` config field (replaces the hardcoded 200 cap on raw observations), and new `memory_summary_history_max: int = 200` config field (caps the retained summary history)

How this reaches the LLM's advice:
- `src/drawing_coach/feedback_engine.py` — `_build_system_prompt` accepts optional `coach_notes: str`, appended at the end of the assembled prompt (after the persona/style/custom-instructions/mode-template prefix)

Settings and UI:
- `src/drawing_coach/settings_dialog.py` — new "Memory" tab exposing `memory_resummarize_interval`, `memory_max_observations`, and `memory_summary_history_max` as user-editable spin boxes, alongside the existing LLM/Capture/Stuck Detection/History tabs
- New `src/drawing_coach/memory_viewer.py` — `MemoryViewerDialog`: grouped list, delete, clear (both files), export (both files)
- New `src/drawing_coach/progress_panel.py` — `ProgressPanel`: theme counts + session timeline
- `src/drawing_coach/main_window.py` — wire memory store into feedback flow; add Memory/Progress menu entries

No new third-party dependencies (json, collections.Counter, datetime all stdlib); re-summarisation reuses the existing LiteLLM client, no new dependency.
