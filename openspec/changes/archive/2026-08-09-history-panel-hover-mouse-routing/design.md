## Context

The Session History row hover-highlight took several seconds to respond on macOS. The full attempt history is in the archived `gui-thread-stall-diagnostics` change and in `.tmp/histor-latency-progress.md`. Four attempts failed:

| # | Change | Result |
|---|---|---|
| 1 (`7ccb255`) | Replaced Enter/Leave on the row widget with viewport mouse-move tracking + `itemAt()` | **Introduced this defect** |
| 2 (`9e90864`) | `WA_StyledBackground` on `_FrameRowWidget` | Fixed a paint bug, blamed for latency |
| 3 (`58e62f9`) | Painted hover directly in `paintEvent()` | No effect on latency |
| 4 (reverted) | Cached thumbnails + `Image.reduce()` | No effect on latency |

Attempts 2–4 were all edits to code that the eventual measurement showed costs **1.9 ms per 68 repaints**. They were validated only on Linux/Xvfb, which does not reproduce the macOS symptom.

### What the measurement showed

The `perf-diagnostics` instrumentation shipped in `gui-thread-stall-diagnostics` reported, while the cursor was over the list:

```
move=376  active=HistoryPanel  move_to=QWindow:188,QLabel:154,_FrameRowWidget:27,QWidget:7
history.hover_hit_test  n=1   (per 5s window)
```

~370 mouse moves per 5 s arriving at the process, routed to `QLabel` and `_FrameRowWidget`, and essentially none reaching the viewport where the hover filter lives. The GUI thread recorded **zero stalls** throughout — it was idle, waiting for input that was being delivered elsewhere.

### Root cause

`HistoryPanel.__init__` installs its event filter on `self._list_widget.viewport()`. `setItemWidget()` places a real `_FrameRowWidget` over the viewport for every row, and that row's `QHBoxLayout` fills it with two `QLabel`s. Qt delivers a mouse move to the topmost widget under the cursor, so the viewport only ever saw moves that landed on the 4px/2px layout margins. Hover therefore updated sporadically, seconds apart.

Attempt 1's justification — recorded in a code comment as *"Enter/Leave delivery to a `setItemWidget()` child is unreliable on macOS"* — is contradicted by the same log, which shows `enter=50 leave=48` in the window where hover was failing. Enter/Leave were working; attempt 1 replaced them with a mechanism that structurally could not receive events.

## Goals / Non-Goals

**Goals:**

- Make the hover highlight track the cursor without perceptible delay, by ensuring the hover tracker actually receives mouse moves.
- Preserve every existing row behaviour: delete button, double-click to open, lookback border, hover text colour.
- Leave a test that fails if row mouse-event routing regresses again.

**Non-Goals:**

- Reverting attempts 2 and 3. The `paintEvent()`-based hover painting is what makes the highlight paint at all on macOS, and it is cheap.
- Reworking `_render()`'s full rebuild, thumbnail cost, or the connection leak. All confirmed, all separate, none of them the hover defect.

## Decisions

### D1 — Make the row and its labels transparent to mouse events, rather than moving the filter

The alternative was to install the event filter on every row widget and every label, or to revert to Enter/Leave on the row. Transparency is better on three counts:

- It keeps a single filter on a single long-lived object, instead of N filters that must be installed and removed as rows are rebuilt on every `frames_changed`.
- It keeps the existing, already-tested `itemAt()` hit-testing path, which the measurement showed costs 0.02 ms per event.
- It generalises: any label added to a row later is covered by the same rule, whereas a per-widget filter would silently miss it.

Qt does not apply `WA_TransparentForMouseEvents` to children, so the attribute must be set on the row **and** on each non-interactive child, while the delete button is left alone and stays clickable. That asymmetry is the one subtlety a future reader needs, so it is stated in the requirement rather than left to the code comment.

### D2 — Move double-click to `QListWidget.itemDoubleClicked`

A mouse-transparent row cannot receive `mouseDoubleClickEvent`. The list view already emits `itemDoubleClicked` with the activated item, and the frame is already stored on the item via `setData(UserRole, frame)` for the lookback indicator — so the handler is a lookup, not new state. This is also more idiomatic: activation is a view concern.

### D3 — Drive the double-click tests through the viewport

The existing tests called `qtbot.mouseDClick(row_widget, ...)`, sending the event straight to the row. That bypasses hit-testing entirely, so they would have passed even with the row unreachable — the same false-green as validating on Xvfb, and the reason this regression shipped. They now send to `lw.viewport()` at the item's rect.

Events are constructed directly rather than synthesised with `QTest`, matching the convention the hover tests already use and document: `QTest`'s double-click is not delivered reliably under Xvfb/offscreen (verified — a constructed press/release/dblclick sequence works, `QTest.mouseDClick` does not).

### D4 — Add a structural test alongside the behavioural one

`test_mouse_move_over_a_row_reaches_the_viewport_filter` asserts `viewport().childAt(centre) is None` — that is the exact hit-test Qt performs to route the event, so it fails for the original defect. The structural test asserting the attributes is kept as well, because it names *why* in the failure message when someone adds an opaque child.

### D5 — Fix the hotkey listener lifecycle in the same change

`_start()` overwrote `self._listener` without stopping the previous one, so `MainWindow`'s `set_hotkey()` + `start()` pair at `main_window.py:215-216` orphaned a listener at every launch. This surfaced as two live pynput Darwin threads in the diagnostic stack dump. It is unrelated to the hover defect — it was investigated as a suspect and cleared — but it violates the existing `stuck-detection` requirement that reconfiguring a hotkey unregisters the old one, and it is a one-line fix, so it is recorded here rather than deferred.

## Risks / Trade-offs

- **A future interactive child of `_FrameRowWidget` will silently not work** if the author expects the row's own mouse events → stated in the requirement and enforced by the structural test, which asserts non-interactive children are transparent and the delete button is not.
- **`childAt()` is an implementation-adjacent assertion** → paired with the behavioural assertion that `_hovered_row` actually updates, so the test still means something if Qt's routing internals change.
- **The input probe is an application-level event filter**, i.e. it runs for every event in the process → it is a dict increment behind an `ON` check, and it is created only when instrumentation is enabled.

## Verification

- `xvfb-run -a uv run pytest` — full suite green (417 tests).
- Confirmed on the affected macOS machine by the reporting user: the history tab is responsive and the hover highlight follows the cursor.
