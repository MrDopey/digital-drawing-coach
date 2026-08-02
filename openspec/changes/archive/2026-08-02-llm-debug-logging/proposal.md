## Why

When LLM feedback (especially overlay annotations) looks wrong, there is currently no way to inspect what the app actually sent to the LLM or what the LLM actually returned — none of the app's `litellm.completion()` call sites persist their request or response. This includes `FeedbackEngine`'s two internal request paths (a structured-output attempt via `_call_structured`, with a process-lifetime fallback to prose parsing via `_call_prose` once structured output fails — see the `structured-json-output-fallback` change now on `main`): whether a given response came from the structured path or the prose fallback materially affects how annotation JSON gets produced, so distinguishing the two is itself a diagnostic need this change should serve. Persisting the raw request (images + text) and raw response on demand would let a user (or developer) capture direct evidence for any bad LLM interaction — not just feedback requests — without re-triggering it live in front of the app's author.

## What Changes

- Add a new "Debug logging of LLM input/output" setting, off by default, exposed as an explicit toggle in the Settings UI (not just an env var) — since enabling it persists screenshots of the user's drawing session to disk, it must be opt-in and visible, not silently enabled by an existing log-level env var.
- When enabled, persist to disk, per call, for **every LLM call the application makes**:
  - `FeedbackEngine._call_structured()` and `FeedbackEngine._call_prose()` — the structured-output attempt and prose fallback, across all four feedback modes (Quick Hint, Full Critique, Practice Exercise, Overlay). A request may produce one or two logged calls depending on whether the structured attempt succeeds.
  - `diagnostics.check_llm()` — the Diagnostics dialog's LLM connectivity check.
  - `SettingsDialog._test_connection()` — the Settings "Test Connection" button.
  - `MemoryStore._try_resummarize()` — periodic coach's-notes re-summarisation.
  - Persisted per call: any image(s) sent (as PNG files, when present — only the feedback paths send images), the full text/content actually sent (system + user messages), and the complete raw response text (or the error, if the call failed).
  - Each call's debug label distinguishes which path produced it (e.g. `feedback_overlay_structured` vs. `feedback_overlay_prose`), so a structured-output failure and its fallback are both visible and attributable.
- Implemented via LiteLLM's own `CustomLogger` callback hook (`litellm.callbacks`), registered once at startup — not by hand-wiring a logging call into each call site. Each call site only adds a `metadata={"debug_label": "..."}` kwarg to its existing `litellm.completion()` call so the callback can name its output; LiteLLM invokes the callback automatically for every call, success or failure, including any future call site that's added later.
- Debug artifacts are written to a dedicated directory under the app's existing XDG config/data location (alongside `memory.json` / `.env`), grouped per call with a timestamped name.
- Document the debug log directory path in the README so it's discoverable without a UI to browse it.
- Purely additive: no change to the existing request/response flow, the annotation JSON schema, or feedback rendering logic at any call site.

## Capabilities

### New Capabilities
- `llm-debug-logging`: A settings-gated, opt-in capability that persists the raw request content (images and/or text) and raw response (or error) to disk for every LLM call the application makes, for offline debugging.

### Modified Capabilities
(none — this is additive instrumentation only; existing request/response/rendering behavior is unchanged)

## Impact

- `src/drawing_coach/llm_config.py`: new persisted setting (default off).
- `src/drawing_coach/settings_dialog.py`: new checkbox in the LLM tab.
- New `src/drawing_coach/llm_debug_log.py`: a `litellm.integrations.custom_logger.CustomLogger` subclass, registered once at app startup via `litellm.callbacks`.
- `src/drawing_coach/feedback_engine.py`: both `_call_structured()` and `_call_prose()` add a `metadata={"debug_label": "..."}` entry via the shared `_base_kwargs()` helper.
- `src/drawing_coach/diagnostics.py`, `src/drawing_coach/memory_store.py`, `src/drawing_coach/settings_dialog.py` (`_test_connection`): each adds one `metadata={"debug_label": "..."}` entry to its existing `litellm.completion(**kwargs)` call — no other change to return values, error handling, or control flow.
- `README.md`: document the debug log directory path.
- No change to `overlay_renderer.py`, the annotation JSON schema, or any existing spec's requirements.
