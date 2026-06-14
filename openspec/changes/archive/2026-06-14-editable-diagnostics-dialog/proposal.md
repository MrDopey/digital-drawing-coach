## Why

When a diagnostic check fails, users cannot select or copy the error message or hint — the text is rendered in plain `QLabel` widgets with no text-interaction flags. This makes it impossible to paste the error into a support channel or search engine without retyping it manually.

## What Changes

- Each check's message and hint text becomes **selectable and copyable** with the mouse (set `TextSelectableByMouse | TextSelectableByKeyboard` on each message label)
- A **"Copy Report"** button is added to the button row — clicking it copies a plain-text summary of all completed check results (name, pass/fail, message, hint if any) to the clipboard, ready to paste for help

## Capabilities

### New Capabilities

- `diagnostics-copyable-results`: Check result messages and hints can be selected and copied by the user; a "Copy Report" button copies all results as plain text to the clipboard.

### Modified Capabilities

- `system-diagnostics`: Message labels must allow text selection; layout rules (word-wrap, minimum width) are applied consistently so selected text reflows correctly.

## Impact

- `src/drawing_coach/diagnostics.py` — `DiagnosticsDialog`: add text-interaction flags to each `msg_lbl`; add "Copy Report" button; store completed results for the copy action
- `tests/test_diagnostics.py` — add test that message labels are text-selectable and that "Copy Report" produces correct output
