## ADDED Requirements

### Requirement: Frame write failures invoke an error callback

The system SHALL provide an `on_write_error: Callable[[Path, Exception], None] | None` attribute on `CaptureEngine`. When `img.save()` raises an exception in `_write_frame`, the system SHALL call `on_write_error` (if set) with the target path and the exception, and SHALL emit a WARNING log with the path and exception details.

#### Scenario: Frame write fails with an OS error

- **WHEN** `img.save()` raises an exception (e.g. disk full, permission denied)
- **THEN** a WARNING log is emitted: `Frame write failed: <path>` with `exc_info=True` attached
- **THEN** `on_write_error(path, exc)` is called if the callback is set

#### Scenario: No callback is set

- **WHEN** `on_write_error` is `None` and `img.save()` raises an exception
- **THEN** only the WARNING log is emitted; no error is raised

### Requirement: Status bar shows a persistent write-failure warning

The main window SHALL display a `QStatusBar` pinned to the bottom of the window. When a write failure occurs the status bar SHALL show the text: "⚠ Frame saves failing — images will be lost if the app closes." The warning SHALL remain visible until the next successful frame write clears it.

#### Scenario: First frame write fails

- **WHEN** `on_write_error` fires for the first time in a session
- **THEN** the status bar displays the one-line warning message

#### Scenario: Write failure recurs

- **WHEN** `on_write_error` fires again while the warning is already shown
- **THEN** the status bar text remains unchanged (no flicker)

#### Scenario: Subsequent frame write succeeds

- **WHEN** `on_frame_captured` fires after a period of write failures
- **THEN** the status bar warning is cleared

### Requirement: Status bar warning text is selectable and copyable

The warning label in the status bar SHALL allow the user to highlight and copy its text using mouse or keyboard selection.

#### Scenario: User selects the warning text

- **WHEN** the user clicks and drags over the status bar warning label
- **THEN** the text is highlighted and can be copied to the clipboard

### Requirement: Hovering the status bar warning shows a copyable error popup

When the user hovers the mouse over the status bar warning, the system SHALL display a popup above the status bar containing the full error detail and permission-fix instructions. The popup text SHALL be selectable and copyable by the user.

#### Scenario: User hovers the status bar warning

- **WHEN** the user moves the mouse over the status bar warning label
- **THEN** a popup appears showing: the failed path, the exception message, and instructions to check the sessions directory, disk space, and (on macOS) Privacy & Security → Files and Folders

#### Scenario: User moves the mouse away

- **WHEN** the user moves the mouse off the status bar warning label
- **THEN** the popup is hidden

#### Scenario: User highlights text in the popup

- **WHEN** the popup is visible and the user clicks and drags over its text
- **THEN** the text is highlighted and can be copied to the clipboard
