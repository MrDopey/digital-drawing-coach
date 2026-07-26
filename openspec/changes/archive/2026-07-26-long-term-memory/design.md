## Context

`FeedbackEngine._build_system_prompt` currently assembles the system prompt from a fixed base prompt, an optional style fragment, optional custom instructions, and a mode template. There is no injection point for cross-session context. Sessions are identified by their directory name (`YYYY-MM-DD_HHMMSS`); `sessions_dir()` is the data root. Neither `memory.json` nor `memory_summaries.json` exist today.

## Goals / Non-Goals

**Goals:**
- `memory.json` (observations) and `memory_summaries.json` (summary history) persist across sessions in the app data directory
- Observations extracted from (or alongside) each LLM feedback response
- Coach's notes appended to every subsequent system prompt without disturbing the cacheable prefix
- Memory viewer and progress panel accessible from the main window
- Every config field this change introduces (`memory_resummarize_interval`, `memory_max_observations`, `memory_summary_history_max`) is editable from the Settings dialog, not just `config.json`

**Non-Goals:**
- Automatic observation extraction via a separate LLM call on every feedback (too slow/expensive for v1; structured extraction is deferred)
- Re-summarising the coach's notes on every request (notes are raw between condensation passes; re-summarisation only runs every `memory_resummarize_interval` responses, default 20)
- Per-category observation limits (flat cap on total observations, configurable but not split by category)
- Syncing memory across devices

## Decisions

### 1. Observation extraction: parse structured JSON block from LLM response (v1)

The LLM is asked (via a mode-agnostic system prompt addition) to append a `<!-- observations: [...] -->` HTML comment to its response containing a JSON array of `{category, note}` objects. `MemoryStore.extract_observations(response_text)` parses this comment and strips it before display. If absent or malformed, no observations are recorded for that response.

**Alternative considered:** second LLM call to extract observations — rejected for v1 (doubles cost and latency). Can be upgraded later.

### 2. Observations and summary history live in two separate files: `memory.json` and `memory_summaries.json`, both siblings of `sessions/`

`paths.memory_path()` returns `sessions_dir().parent / "memory.json"` (raw observations); a new `paths.memory_summaries_path()` returns `sessions_dir().parent / "memory_summaries.json"` (the summary history and its `last_resummarized_count` counter). Both live in the same XDG data directory as sessions and are easy to back up.

**Alternative considered:** keep both lists in a single `memory.json` (`{"observations": [...], "summaries": [...], "last_resummarized_count": N}`) — rejected in favour of two files. The lists grow at very different rates (one entry per response vs. one entry per `memory_resummarize_interval` responses) and have independent caps (`memory_max_observations` vs. `memory_summary_history_max`); separate files make each file's schema simpler to reason about, let power users inspect/back up/delete one without touching the other (e.g. wipe the condensation history but keep the raw log, or vice versa), and avoid a single larger file being rewritten on every observation append when only the observation half actually changed.

### 3. `MemoryStore` is a thin wrapper: load-on-init, mutate in memory, save-on-change

`MemoryStore` loads both files on first access and exposes `append(obs)`, `delete(idx)`, `clear()`, `save()`, and `summarise(max_observations=20) -> str`. `summarise` returns a brief "coach's notes" Markdown block that becomes prompt context. Saving is synchronous on mutation — each file stays small (well under 50 KB even at the default caps) — and only the file whose list actually changed is rewritten (appending an observation does not touch `memory_summaries.json`, and vice versa).

`append`'s prune threshold reads `LLMConfig.memory_max_observations` (default 200) rather than a hardcoded constant — see Decision 8. The summary history in `memory_summaries.json` (see Decision 5) is pruned against its own `LLMConfig.memory_summary_history_max` (default 200). `MemoryStore.clear()` resets both files — the raw observation list, the summary history, and the `last_resummarized_count` counter — since "Clear All Memory" in the viewer is meant to be a full reset, not a partial one.

### 4. Coach's notes context: `FeedbackEngine._build_system_prompt` accepts `coach_notes: str = ""`, appended at the end

`MainWindow` (or the feedback trigger path) calls `memory_store.summarise()` and passes it to `request_feedback(..., coach_notes=...)`. `_build_system_prompt` **appends** it *after* the mode template — it does not prepend it before the persona text. The base prompt, style fragment, custom instructions, and mode template form a stable prefix that is byte-identical across requests; putting the only per-session/per-response-varying content (`coach_notes`) at the end means providers that cache prompt prefixes (Anthropic prompt caching, OpenAI automatic caching, etc.) still get a cache hit on that prefix on every request, instead of invalidating the cache on every call because the notes changed near the front. Session count is passed as part of the notes block (e.g. "You have worked with this student across N sessions.").

**Alternative:** `MemoryStore` is injected into `FeedbackEngine` constructor — tighter coupling; the parameter approach keeps the engine testable without a store.

**Alternative considered:** prepend notes before the persona (original v1 draft) — rejected because it makes the notes block part of the cached prefix, so the prefix changes on every new observation and the cache is invalidated on (almost) every request, defeating the purpose of caching the (large, static) base persona text.

### 5. Coach's notes: raw between condensation passes; each condensation is appended to a persisted, separately-capped summary history, and only the *most recent* summary feeds the LLM

`summarise()` formats the raw observations directly (e.g. a bulleted `category: note` list, most-recent N, deduplicated) between condensation passes — most `summarise()` calls make no LLM call. Since this block is exactly what gets injected into the LLM system prompt to produce coaching advice, it needs to stay compact and high-signal rather than growing unboundedly, so periodic condensation is on by default rather than requiring the user to discover and enable a setting.

A new config field, `LLMConfig.memory_resummarize_interval: int = 20`, controls the condensation cadence:
- `N > 0` (default `20`): `MemoryStore` tracks how many observations have been appended since the last re-summarisation. Once that count reaches `N`, the *next* call that would build coach's notes instead triggers one LLM call that condenses the accumulated raw notes (since the last summary, plus the prior summary's text if one exists) into a shorter block.
- `0`: opts out entirely; notes stay raw forever and `summarise()` always formats from the live observation list, never calling the LLM.

Each successful condensation is **appended** as a new `Summary(date, text, observation_count)` entry to the `summaries` list in `memory_summaries.json` — a running history, kept in its own file separate from the raw observations in `memory.json` (see Decision 2) — rather than overwriting the previous summary in place. This preserves an audit trail of how the coach's understanding of the student condensed and evolved over time (useful for later export/inspection), even though only one summary is ever active in a prompt at a time.

For this prompt context, `summarise()`'s output is built from the **most recent** entry in `summaries` (if any) plus the raw observations appended since that entry's `date` — not a concatenation of the whole history. This keeps the block bounded regardless of how long the summary history grows.

Like the raw observation cap, the summary history has its own cap: `LLMConfig.memory_summary_history_max: int = 200`. When appending a new summary would exceed it, the oldest summaries are pruned first (mirroring `memory_max_observations`'s pruning behaviour for raw observations).

This bounds the coach's notes block from growing unboundedly in token count over a long-lived store (a power user with 200 raw observations would otherwise send a large notes block on every request), while still amortising the extra LLM call across 20 responses rather than paying it on every request.

**Alternative considered:** overwrite a single `current_summary` field in place instead of keeping history — rejected; loses the audit trail of how the coach's notes evolved, which the Memory Viewer or a future export could otherwise surface, for negligible extra storage (a Markdown paragraph per condensation, capped like everything else).

**Alternative considered:** concatenate multiple recent summaries (not just the latest) into the injected block — rejected for v1; each summary already condenses everything before it, so concatenating would re-include information the newest summary already subsumes. Only the latest is needed for the LLM; older entries exist purely as history.

**Alternative considered:** always re-summarise on every request — rejected, doubles latency/cost per feedback request, the same reason a second extraction call was rejected in Decision 1.

**Alternative considered:** default to disabled (`0`), requiring users to opt in via config — rejected because the coach's notes block is the actual content driving the LLM's advice; leaving it to grow raw and unbounded by default would silently degrade advice quality (and eventually prompt size/cost) for users who never discover the setting.

**Alternative considered:** summarise on a wall-clock timer (e.g. daily) instead of a response count — response count is simpler to reason about, test deterministically, and ties directly to store growth rather than session cadence.

### 6. Memory viewer: `MemoryViewerDialog` sorted by category then reverse date

`QTreeWidget` with top-level items per category, child items per observation (`date — note`). Delete button removes the selected observation. Clear All triggers `QMessageBox` confirmation and clears both `memory.json` and `memory_summaries.json`. Export uses `QFileDialog.getExistingDirectory` and copies both `memory.json` and `memory_summaries.json` into the chosen directory (a single-file save dialog no longer fits now that memory spans two files). Read-only summary text area at the top shows the current coach's notes block.

### 7. Progress panel: `ProgressPanel(QWidget)` added as a tab in Settings or as a standalone dialog

Lists categories with observation counts and session counts (e.g. "Perspective: 7 observations across 4 sessions"). Below: session date timeline as a simple `QListWidget` of session start dates loaded from `sessions_dir()` meta files.

### 8. Observation cap and summary-history cap are configurable, and every new config field gets a Settings control

`LLMConfig.memory_max_observations: int = 200` replaces the hardcoded 200 in `MemoryStore.append`, and `LLMConfig.memory_summary_history_max: int = 200` bounds the `summaries` list from Decision 5. All three new config fields introduced by this change (`memory_resummarize_interval`, `memory_max_observations`, `memory_summary_history_max`) are exposed as `QSpinBox` controls on a new "Memory" tab in `SettingsDialog`, following the existing pattern (LLM/Capture/Stuck Detection/History tabs each expose their own `LLMConfig` fields). This closes the gap the original v1 draft of this change left open ("cap is configurable via `config.json` in a future iteration; hardcoded for v1") — since all three fields live in the same new `MemoryStore`/Settings surface this change is already building, there is no reason to defer their UI exposure to a follow-up change.

**Alternative considered:** leave the caps hardcoded and only expose `memory_resummarize_interval` — rejected; the raw-observation cap was already flagged as an arbitrary hardcoded value in the original draft, and the summary-history cap is the same kind of value on a newly-introduced list — adding both spin boxes to the same new tab is marginal cost compared to the overhead of a separate follow-up proposal.

**Alternative considered:** share a single cap config between raw observations and the summary history — rejected; the two lists grow at very different rates (one entry per response vs. one entry per `memory_resummarize_interval` responses) and serve different purposes (detailed record vs. audit trail of condensations), so a single shared number would be the wrong size for at least one of them.

## Risks / Trade-offs

- [LLM may not always emit the `<!-- observations -->` comment] → silently ignored; memory degrades gracefully to empty rather than erroring
- [Observation quality depends on LLM compliance] → acceptable for v1; structured extraction via second call can replace this later
- [Re-summarisation is itself an LLM call and can fail/time out] → on failure, keep the existing raw/summary notes unchanged and log a debug entry; never block the feedback request on it
- [Re-summarisation is an extra LLM call, now on by default] → amortised over N (default 20) responses rather than per response, and users can set `memory_resummarize_interval = 0` to opt out and keep notes raw forever
