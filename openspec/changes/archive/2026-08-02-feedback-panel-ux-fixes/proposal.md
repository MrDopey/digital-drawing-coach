## Why

The feedback panel currently has several usability problems: its title ("Get Feedback") no longer matches what the panel actually does (manage/view feedback and history, not just request it), opening it silently fires an LLM API call before the user has asked for anything (wasting quota/cost and surprising the user), the overlay image and text feedback share a fixed-height split so neither gets enough room, and the feedback text itself has no scrollbar — long responses are simply clipped and unreadable.

## What Changes

- Rename the "Get Feedback" panel/window title to "Feedback Management".
- Opening the feedback panel SHALL NOT trigger an LLM API call. Feedback requests SHALL only fire when the user explicitly triggers them (e.g. via the existing mode-row trigger button).
- The overlay (top) and feedback text (bottom) sections SHALL be split with a user-draggable divider (`QSplitter`) instead of a fixed layout, so the user can resize each half.
- The feedback text area SHALL be wrapped in a scrollable container (`QScrollArea` or a scrolling text widget) so feedback content longer than the visible area can be scrolled instead of being cut off.
- The overlay (top) section SHALL support zooming in/out on the annotated image, independent of splitter resizing, via zoom controls (and `Ctrl+Wheel`).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `feedback-modes`: panel title changes to "Feedback Management"; opening the panel no longer triggers a feedback request automatically; the feedback text region becomes scrollable.
- `overlay-feedback`: the overlay/feedback layout becomes a user-resizable split (QSplitter) instead of a fixed-proportion layout, and the overlay image gains zoom in/out/reset controls.

## Impact

- Affected UI: the feedback panel window class (title, initial-open behavior) and the overlay+feedback layout widget within it.
- No changes to LLM request/response handling, only to when/how requests are triggered from the UI and how results are laid out and scrolled.
- No API or data model changes.
