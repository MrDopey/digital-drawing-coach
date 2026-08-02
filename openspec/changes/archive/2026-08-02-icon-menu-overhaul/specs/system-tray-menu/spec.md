## ADDED Requirements

### Requirement: Tray menu top item restores the main window
The system tray icon's context menu SHALL have, as its first item, an action that shows the main window — the same window instance shown when a session starts — bringing it to the front and giving it focus, regardless of whether it is currently hidden or already visible.

#### Scenario: Restoring a hidden main window
- **WHEN** the main window has been closed to tray (hidden, capture still running) and the user selects the top tray menu item
- **THEN** the same main window instance is shown, raised above other windows, and given input focus

#### Scenario: Selecting restore while the main window is already visible
- **WHEN** the main window is already visible and the user selects the top tray menu item
- **THEN** the main window is raised and given input focus without error or duplication

### Requirement: Double-clicking the tray icon restores the main window
Double-clicking the system tray icon SHALL trigger the same restore behavior as the tray menu's top item (show, raise, and focus the main window), without requiring the menu to be opened. Other tray icon activation reasons (single click, middle click) SHALL NOT trigger this behavior.

#### Scenario: Double-clicking a hidden tray icon
- **WHEN** the main window is hidden and the user double-clicks the tray icon
- **THEN** the same main window instance is shown, raised above other windows, and given input focus

#### Scenario: Single-clicking the tray icon
- **WHEN** the user single-clicks the tray icon
- **THEN** the main window is not shown or raised as a result

### Requirement: Tray menu excludes panel shortcuts available elsewhere
The system tray icon's context menu SHALL NOT contain "Get Feedback", "Memory", or "Progress" items. These actions remain reachable from the main window's button row.

#### Scenario: Tray menu contents after opening
- **WHEN** the user right-clicks the tray icon
- **THEN** the menu shows exactly: the restore action, a separator, Pause/Resume Capture, Settings, a separator, About, and Quit — with no Get Feedback, Memory, or Progress entries
