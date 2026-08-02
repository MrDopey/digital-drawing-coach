## Context

`FeedbackEngine.request_feedback` (`feedback_engine.py`) makes one `litellm.completion()` call per feedback request and gets back a single prose string. Two different sub-payloads are currently embedded in that prose and pulled out with regex:

- Memory observations: the system prompt asks the model to append `<!-- observations: [{"category": ..., "note": ...}] --> ` at the end of its reply. `MemoryStore.extract_and_append` (`memory_store.py:132`) regexes this out, JSON-parses the captured group, and strips the comment from the displayed text.
- Overlay annotations: in `overlay` mode, the system prompt asks for a ` ```json ... ``` ` fenced block with an `annotations` array. `_extract_json_block`/`_strip_json_block` (`feedback_engine.py:231`) regex it out.

Both extractions fail silently (return `None`/unchanged text) if the model's formatting drifts even slightly — no distinction between "model chose not to annotate" and "regex didn't match." LiteLLM exposes `response_format={"type": "json_schema", "json_schema": {...}, "strict": True}` for providers that support OpenAI-style structured outputs (this app is provider-agnostic via LiteLLM, including local Ollama models, which do not reliably support this).

## Goals / Non-Goals

**Goals:**
- Use structured output as the primary path for the vision feedback call, returning feedback text + observations (+ annotations in overlay mode) as one validated JSON object.
- Preserve current behavior byte-for-byte when structured output isn't supported or fails: same system prompt content, same regex extraction, same user-visible text and error messages.
- Keep the fallback decision local to `FeedbackEngine`/`MemoryStore` — no new config flags, no user-visible mode switch.

**Non-Goals:**
- Not changing the resummarization call in `memory_store.py::_try_resummarize` — it returns free-form condensed prose by design (a summary paragraph, not structured records), so there's no structured payload to extract there.
- Not changing what's rendered in the feedback panel or how overlay annotations are drawn — only how the data reaches those renderers.
- Not adding a settings toggle for structured vs. prose mode; the fallback is automatic and transparent.

## Decisions

**One schema, mode-conditional fields.** Rather than one schema per mode, use a single JSON schema with `feedback_text` (string, required), `observations` (array of `{category, note}`, required, may be empty), and `annotations` (array, optional/only populated for `overlay` mode). Rationale: one schema is simpler to maintain than four, and unused fields are cheap for the model to leave empty — the alternative (a schema per mode) mirrors the existing `_MODE_TEMPLATES` split but roughly quadruples the schema surface for no behavioral benefit.

**Fallback trigger: attempt once per application launch, then disable via a process-lifetime flag.** `request_feedback` attempts the structured call only while a module-level flag `_structured_output_disabled` is `False` (initialised `False` at process start). If `litellm.completion()` raises for the structured attempt (unsupported `response_format`, provider error) or the response fails to parse/validate against the expected shape, the code sets `_structured_output_disabled = True` and falls back to today's exact prompt+regex path for that request. Every subsequent `request_feedback` call for the remainder of the process, regardless of which `FeedbackEngine` instance makes it, checks the flag first and skips the structured attempt entirely, going straight to the prose path. The flag only resets when the application restarts (fresh process, fresh module state). Rationale: this is what the user explicitly asked for — a single, one-time detection rather than a per-request retry — and it avoids paying a failed round-trip on every request for a model that will never support structured output. Trade-off vs. the per-request-retry alternative: a single *transient* failure (e.g. a network blip during the structured attempt, not an actual lack of support) permanently disables structured output for the rest of the session, even though the provider does support it. This is accepted because (a) the prose fallback path fully replicates today's working behavior, so nothing breaks, and (b) the one-time warning tells the user how to recover (restart the app).

**Global flag lives at module scope, not on `FeedbackEngine`.** `_structured_output_disabled` is a module-level variable in `feedback_engine.py`, not an instance attribute, so it is shared across the lifetime of the process even if `FeedbackEngine` is ever reconstructed (e.g. after a settings change that swaps the configured model). A getter/setter pair (or a small internal helper) is exposed so tests can reset the flag between test cases without reaching into module internals directly.

**One-time warning via a new engine callback.** `FeedbackEngine` gains `on_structured_output_unavailable: Callable[[str], None] | None`, invoked exactly once — at the moment the flag transitions from `False` to `True` — with a user-facing message. `main_window.py` wires this to `QMessageBox.warning(self, "Structured Output Unavailable", message)`, consistent with the existing warning pattern used for e.g. the "Window Closed" notice (`main_window.py:446`). The callback fires from within `request_feedback`, after the fallback prose call completes successfully, so the warning appears alongside (not instead of) that request's normal feedback response.

**`FeedbackResponse` gains a `source` marker, not a shape change.** `FeedbackResponse.text`/`.annotation_json` keep their current types (str / optional JSON string) regardless of which path produced them, so `main_window.py` and the overlay renderer need no changes. Internally, structured-path observations are handed to `MemoryStore` as already-parsed dicts (new `append_structured` entry point) instead of round-tripping through the HTML-comment-in-text format only to be immediately regexed back out.

**`memory_store.py` extraction becomes two entry points, not one branching function.** Add `MemoryStore.append_observations(items, session_id)` (accepts pre-parsed `{category, note}` dicts — used by the structured path) alongside the existing `extract_and_append(response_text, session_id)` (regex path, used by the fallback). `FeedbackEngine` calls whichever matches how it got its data; `MemoryStore` doesn't need to know or guess which path produced its input.

## Risks / Trade-offs

- **[Risk]** LiteLLM's structured-output support varies by provider/model and can raise different exception types (or none, and just return unparsable content) → **Mitigation**: wrap both the call and the response-parsing/validation in one try/except that sets the disable flag and triggers the prose fallback; treat "parsed but missing required fields" the same as "raised an exception."
- **[Risk]** A single transient failure (network blip, momentary provider hiccup) during the one launch-time attempt permanently disables structured output for the rest of the session, even for a model/provider that does support it → **Mitigation**: the prose fallback path is fully functional (identical to pre-change behavior), so no feature actually breaks; the one-time warning explicitly tells the user to restart the app to retry, giving a clear recovery path. Accepted as the intended behavior per explicit product decision, not treated as a bug to engineer around.
- **[Risk]** The first request of a session pays for a failed structured attempt before falling back, adding latency to that one request only → **Mitigation**: this is a one-time cost per launch (not per request), and the existing 10s rate-limit gate already bounds how often requests happen.
- **[Risk]** Divergence between the structured schema's field semantics and the prose prompt's instructions over time (e.g. someone updates one but not the other) → **Mitigation**: derive both the JSON-schema property descriptions and the prose-mode instructions from the same shared constants where practical (e.g. category examples, annotation type definitions) rather than duplicating free text.
- **[Risk]** Module-level global state is easy to leak between test cases if not reset → **Mitigation**: expose an internal reset helper used only by tests (e.g. in a fixture/teardown), documented in the test file rather than as public API.

## Open Questions

None — the fallback behavior and schema shape are fully specified above; implementation can proceed directly to tasks.
