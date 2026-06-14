## Context

`DiagnosticsDialog` in `diagnostics.py` renders each check row using three `QLabel` widgets (status icon, name, message). The message label receives a rich-text string including an optional hint. `QLabel` widgets have no text-interaction flags by default so text cannot be selected or copied.

The dialog also has no way to bulk-copy results — users must read them visually.

## Goals / Non-Goals

**Goals:**
- Make every message/hint label individually selectable with the mouse
- Add a "Copy Report" clipboard action that serialises all completed results as plain text

**Non-Goals:**
- Inline editing of values (not needed — read-only diagnostic output)
- Opening Settings from within the dialog
- Changing the visual layout beyond what's required to keep word-wrap working with selectable text

## Decisions

**Use `setTextInteractionFlags` on `QLabel` rather than switching to `QTextEdit`**
`QLabel` already handles rich-text hints with embedded `<span>` tags. Switching to `QTextEdit` would require stripping HTML for display parity. Setting `TextSelectableByMouse | TextSelectableByKeyboard` on the existing labels is a one-line change per label and preserves all existing rendering. Cursor changes to a text cursor automatically.

**Accumulate completed `CheckResult` objects in a list**
The "Copy Report" button needs the raw results. The `_on_check_done` slot already receives each `CheckResult`; appending to a `list[CheckResult]` (reset on re-run) is sufficient. No threading concerns — the slot runs on the main thread.

**Plain-text report format**
```
[✓] Screen Capture — Screen capture available
[✗] LLM Connection — AuthenticationError: bad key
      Hint: Check your API key, Base URL, and network connection in Settings → LLM
```
Simple and pasteable. No HTML or markdown required.

## Risks / Trade-offs

[Rich-text labels with text selection] → Qt renders selectable rich-text labels with a text cursor but the cursor only appears over the text portion, not the full cell. This is acceptable and standard Qt behaviour.

[Copy Report before checks finish] → Button is disabled while checks are running (existing behaviour for Re-run button), so partial results are not an issue. Alternatively we could enable it and copy whatever is done so far — keep it disabled to avoid confusion.

## Migration Plan

No migration required — purely additive UI change. Existing tests continue to pass; new tests cover the selectable flag and copy output.
