## Why

The coaching LLM currently returns one prose blob per request, with structured data (memory observations, overlay annotations) smuggled inside it as an `<!-- observations: [...] -->` HTML comment or a fenced ` ```json ` block, then pulled back out with regex (`_extract_json_block`/`_strip_json_block` in `feedback_engine.py`, `_OBSERVATIONS_RE` in `memory_store.py`). This is fragile: extraction silently degrades to "leave it as text" whenever the model deviates even slightly from the exact comment/fence format, and there is no way to distinguish "the model chose not to annotate" from "the model's formatting broke the regex." Most LiteLLM-supported providers (OpenAI, Anthropic, and others) support a structured `response_format` mode that guarantees schema-conformant JSON back from a single call, which would let the same request return the user-facing feedback text and the structured observations/annotations as fields of one object instead of a format the app has to reverse-engineer out of prose.

## What Changes

- The feedback-request call in `feedback_engine.py` SHALL request structured output (`response_format={"type": "json_schema", ...}`) from LiteLLM, with a schema whose fields are the visible feedback text, the structured memory observations array, and (for `overlay` mode) the annotations array.
- The system SHALL attempt structured output only **once per application launch**. If that single attempt fails (the configured model/provider does not support strict JSON-schema enforcement, or the parsed response doesn't validate), a process-lifetime flag SHALL be set and every subsequent feedback request for the remainder of the application's run SHALL go directly to the prose-plus-embedded-block prompt and regex extraction — no further structured attempts are made until the application is restarted.
- The first time the flag is set, the system SHALL show the user a one-time warning explaining that structured output is unavailable for this session, that memory extraction and overlay annotations will rely on the less-reliable text-parsing fallback, and that restarting the application will retry structured output.
- `MemoryStore.extract_and_append` SHALL accept already-parsed observation records directly from the structured response as its primary path; the existing `<!-- observations: [...] -->` regex parsing SHALL remain as the fallback path used only when structured output wasn't available for that request.
- Overlay-mode annotation extraction SHALL prefer the annotations field of the structured response; the existing fenced ` ```json ` block parsing SHALL remain as the fallback path.
- No change to what the user sees in the feedback panel or to the annotation rendering itself — this is a request/response-format and parsing-path change, not a UI or behavior change.

## Capabilities

### New Capabilities
(none — this is a parsing/transport change to existing capabilities)

### Modified Capabilities
- `llm-feedback`: the feedback request SHALL prefer structured JSON output (feedback text + observations, and annotations for overlay mode) over embedded-comment prose, attempting it once per application launch and falling back to the current prompt/regex approach for the rest of the run (with a one-time user-facing warning) if that single attempt isn't supported or fails to validate.
- `memory-store`: observation extraction SHALL accept structured observations directly from the LLM response as its primary path, with the existing HTML-comment regex parsing retained as an explicit fallback.
- `overlay-feedback`: annotation extraction SHALL prefer the annotations field of a structured response, with the existing fenced-JSON-block regex parsing retained as an explicit fallback.

## Impact

- Affected code: `src/drawing_coach/feedback_engine.py` (request construction, response parsing, `FeedbackResponse` shape, new process-lifetime disable flag), `src/drawing_coach/memory_store.py` (`extract_and_append` and its call site), overlay annotation handling in `main_window.py` (also wires the new one-time warning dialog).
- Affected dependency: `litellm.completion(..., response_format=...)` — behavior/support varies by provider; the single-attempt-then-disable approach means a transient failure (not just genuine lack of support) will also disable structured output for the rest of the run.
- No config schema changes and no new user-facing settings; purely an internal request/response contract change with a compatibility fallback for providers that don't support structured output (e.g. some local Ollama models), surfaced to the user via a one-time warning dialog rather than a silent per-request retry.
