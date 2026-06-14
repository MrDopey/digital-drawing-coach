## Context

`has_input_monitoring_permission()` in `_backend_macos.py` uses `AXIsProcessTrustedWithOptions` from ApplicationServices. That function checks the macOS **Accessibility** TCC category (`kTCCServiceAccessibility`), not Input Monitoring (`kTCCServiceListenEvent`). These are separate grants: a user can have one without the other.

The `check_input_monitoring` diagnostic function in `diagnostics.py` calls this and, on failure, points to System Settings → Input Monitoring. Because it is actually checking Accessibility, this hint can be wrong in both directions.

Splitting into two dedicated checks (one per TCC category) means each failure message is unambiguous and actionable.

## Goals / Non-Goals

**Goals:**
- `has_accessibility_permission()` returns `True` iff the app holds the macOS Accessibility TCC grant
- `has_input_monitoring_permission()` returns `True` iff the app holds the macOS Input Monitoring TCC grant
- Two separate diagnostic rows on macOS, each with its own targeted hint

**Non-Goals:**
- Requesting either permission at runtime (no TCC prompts triggered)
- Changing behaviour on Linux or Windows

## Decisions

### `has_accessibility_permission` — keep `AXIsProcessTrustedWithOptions`

`AXIsProcessTrustedWithOptions(NULL)` (pass `NULL` / `None` for the options dict) is the documented macOS API for querying Accessibility trust. It is exactly the right tool for this check; no change to the logic, just moving it to the correctly-named function.

### `has_input_monitoring_permission` — use `IOHIDCheckAccess`

`IOHIDCheckAccess(kIOHIDRequestTypeListenEvent)` from IOKit is a query-only API added in macOS 10.15 (Catalina) that directly interrogates the Input Monitoring TCC category. Return values:
- `kIOHIDAccessTypeGranted` (0) — granted → return `True`
- `kIOHIDAccessTypeDenied` (1) — denied → return `False`
- `kIOHIDAccessTypeUnknown` (2) — not yet determined → return `False` (conservative)

**Why not `CGEventTapCreate`?** Creating an event tap has observable side effects (a live tap exists briefly) and requires more cleanup. `IOHIDCheckAccess` is a pure query.

**Why not `IOHIDRequestAccess`?** That function prompts the user. We only want to check, not prompt.

**ctypes binding**: `IOKit` is found via `ctypes.util.find_library("IOKit")`. `kIOHIDRequestTypeListenEvent = 1`. Wrap the whole call in try/except and return `False` on any error (missing library, missing symbol, or OS < 10.15).

### Diagnostic registration order

Add the Accessibility check immediately before the Input Monitoring check in the macOS checks list in `diagnostics.py`, so the two related checks appear together in the dialog.

## Risks / Trade-offs

- **macOS version floor**: `IOHIDCheckAccess` requires macOS 10.15+. Drawing Coach already requires Catalina, so this is not a new constraint. The try/except fallback handles the case if somehow run on an older OS.
- **Two rows instead of one**: The diagnostics dialog gains one extra row on macOS. This is the desired outcome — it is not a regression.
