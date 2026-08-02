## 1. Shared schema definition

- [x] 1.1 In `feedback_engine.py`, define a shared JSON schema constant (`_STRUCTURED_RESPONSE_SCHEMA` or similar) with `feedback_text` (string, required), `observations` (array of `{category, note}`, required), and `annotations` (array, required only in overlay mode) — reusing the existing category examples and `arrow`/`line`/`circle` annotation shape definitions from `_SYSTEM_PROMPT`/`_MODE_TEMPLATES["overlay"]` rather than duplicating the free text
- [x] 1.2 Add a schema-description variant of the system prompt (persona + style + custom instructions + mode template + coach notes, same as today) that omits the `<!-- observations: -->` comment instruction, since structured mode carries observations as a field

## 2. Structured-output request path in `feedback_engine.py`

- [x] 2.1 Add a module-level flag (e.g. `_structured_output_disabled: bool = False`) that persists for the process lifetime, plus a small internal reset helper for test use only
- [x] 2.2 In `request_feedback`, only when the flag is unset, attempt the LiteLLM call with `response_format={"type": "json_schema", "json_schema": {...}, "strict": True}` using the schema from 1.1
- [x] 2.3 Parse and validate the structured response: required fields present and correctly typed; treat missing/invalid `feedback_text` or `observations` as a validation failure
- [x] 2.4 On structured-call exception (unsupported `response_format`, provider error) or validation failure: set the module-level flag to `True`, log at debug level, and fall back to today's exact prose prompt (with the observations-comment instruction) and existing regex extraction (`_extract_json_block`/`_strip_json_block`, `_OBSERVATIONS_RE`-based parsing) for that request
- [x] 2.5 When the flag is already set at the start of `request_feedback`, skip the structured attempt entirely and go straight to the prose path
- [x] 2.6 Add `FeedbackEngine.on_structured_output_unavailable: Callable[[str], None] | None`, invoked exactly once — at the moment the flag transitions `False` → `True` — with a user-facing warning message; ensure it does not fire again on later requests even though the flag stays set
- [x] 2.7 Ensure existing error handling (auth/rate-limit/network/quota/policy-refusal detection in `request_feedback`) applies uniformly regardless of which path (structured or prose fallback) raised the error
- [x] 2.8 Thread the parsed `observations` list and (overlay mode) `annotations` list out of `request_feedback` to the caller alongside the existing `FeedbackResponse` (text, annotation_json) so `MemoryStore` and the overlay renderer can consume them without re-parsing

## 3. `memory_store.py` structured observation path

- [x] 3.1 Add `MemoryStore.append_observations(items: list[dict], session_id: str) -> None` that appends already-parsed `{category, note}` records directly (current-date stamped), reusing the existing cap/prune logic in `append()`
- [x] 3.2 Update the call site in `main_window.py` (currently calling `extract_and_append`) to call `append_observations` when the response came from the structured path, and `extract_and_append` only for the prose-fallback path
- [x] 3.3 Leave `extract_and_append`'s regex-based parsing and stripping behavior unchanged for the fallback path
- [x] 3.4 In `main_window.py`, wire `FeedbackEngine.on_structured_output_unavailable` to `QMessageBox.warning(self, "Structured Output Unavailable", message)`, matching the existing warning style (e.g. the "Window Closed" notice); the message text SHALL state that structured output is unavailable for this session, that memory notes and overlay annotations fall back to less-reliable text parsing, and that restarting the app will retry structured output

## 4. Overlay annotation path

- [x] 4.1 When overlay mode used the structured path, take `annotations` directly from the structured response (already validated in 2.2) instead of regex-extracting a fenced JSON block
- [x] 4.2 When overlay mode fell back to the prose path, keep the existing `_extract_json_block`/`_strip_json_block` fenced-block parsing and the "Visual overlay unavailable" fallback notice on parse failure, unchanged
- [x] 4.3 Confirm annotation rendering (`arrow`/`line`/`circle` compositing in `main_window.py`) requires no changes since both paths produce the same annotation list shape

## 5. Tests

- [ ] 5.1 Add a `feedback_engine` test (with the module-level flag reset beforehand) where the mocked LiteLLM call returns a valid structured response — assert no regex extraction occurs, `observations`/`annotations` are read directly from the structured fields, and the disable flag remains unset
- [ ] 5.2 Add a test where the structured call raises (simulating an unsupported provider) — assert the flag becomes set, the code falls back to the prose prompt and regex extraction for that request, the user still gets a `FeedbackResponse`, and `on_structured_output_unavailable` fires exactly once with a message
- [ ] 5.3 Add a test where the structured call returns invalid/incomplete JSON — assert the same disable-and-fallback behavior triggers and a debug log entry is written
- [ ] 5.4 Add a test that, with the flag already set, calls `request_feedback` twice — assert the structured call is never attempted (mock not called with `response_format`) on either call, and `on_structured_output_unavailable` does not fire again
- [ ] 5.5 Add a `memory_store` test for `append_observations` covering: normal append, cap/prune behavior matching `append()`, and empty-list no-op
- [ ] 5.6 Add an overlay-mode test covering both the structured-annotations path and the prose-fallback fenced-JSON path, asserting identical rendered-annotation output for equivalent input data

## 6. Documentation

- [ ] 6.1 Update `README.md` (developer-facing section covering the LLM integration / feedback flow) to describe the structured-output-first, prose-fallback request behavior
- [ ] 6.2 Update `.claude/CLAUDE.md`'s Tech Stack / LLM row (or add a short note near it) to mention that feedback requests prefer LiteLLM structured JSON output with an automatic prose-parsing fallback for providers that don't support it
- [ ] 6.3 Review `openspec/config.yaml` for a recurring gap this change might reveal (e.g. provider-capability-dependent fallback behavior as a recurring pattern needing its own rule); propose changes only if a clear, recurring gap exists — otherwise leave unchanged

## 7. Verification

- [ ] 7.1 Run `uv run pytest` and confirm all tests pass
