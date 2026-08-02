## MODIFIED Requirements

### Requirement: Three selectable feedback modes
The system SHALL support four feedback modes that determine the depth and format of LLM coaching output. The active mode SHALL be presented as a mode selector in the feedback panel and SHALL persist across the session. The feedback panel SHALL include a "Request Feedback" button that triggers a feedback request using the currently selected mode; this button is the only feedback-panel control that triggers an LLM request.

Modes:
- **Quick Hint**: Single-sentence identification of the most pressing issue
- **Full Critique**: Structured breakdown covering composition, technique, anatomy/perspective, and suggested next steps
- **Practice Exercise**: A targeted drill or exercise based on the detected weakness
- **Overlay**: Visual annotation of the drawing with correction lines, arrows, and labels composited onto the screenshot

#### Scenario: User selects Quick Hint mode
- **WHEN** the user selects the "Quick Hint" mode and feedback is triggered
- **THEN** the LLM response SHALL be a single sentence of no more than 30 words identifying the primary issue

#### Scenario: User selects Full Critique mode
- **WHEN** the user selects the "Full Critique" mode and feedback is triggered
- **THEN** the LLM response SHALL be structured markdown with sections: Composition, Technique, Anatomy/Perspective, and Next Steps

#### Scenario: User selects Practice Exercise mode
- **WHEN** the user selects the "Practice Exercise" mode and feedback is triggered
- **THEN** the LLM response SHALL describe a specific, actionable drawing exercise addressing the identified weakness

#### Scenario: User selects Overlay mode
- **WHEN** the user selects the "Overlay" mode and feedback is triggered
- **THEN** the system sends the overlay annotation prompt to the LLM and renders the returned annotations on the screenshot as described in the overlay-feedback spec

#### Scenario: Mode persists within session
- **WHEN** the user selects a feedback mode and triggers multiple feedback requests
- **THEN** all subsequent requests in the session SHALL use the selected mode until changed

#### Scenario: User triggers feedback from the panel
- **WHEN** the user clicks the "Request Feedback" button in the feedback panel
- **THEN** the system requests feedback using the currently selected mode, identically to triggering feedback via the tray menu's manual re-trigger, the hotkey, or automatic stuck detection

### Requirement: Feedback is displayed in a non-intrusive panel
The system SHALL display feedback in a panel titled "Feedback Management" that does not obscure the drawing application. The panel SHALL be dismissible and repositionable by the user. The panel SHALL open at a default size large enough to display both a full-length text response and a full overlay image without requiring the user to resize it first. The panel's feedback text SHALL always be shown in a scrollable text area, so responses longer than the visible area can be scrolled and read in full rather than being clipped or truncated.

#### Scenario: Feedback panel appears after response
- **WHEN** the LLM returns a response
- **THEN** the feedback panel becomes visible with the rendered markdown content

#### Scenario: User dismisses feedback panel
- **WHEN** the user clicks the dismiss button or presses Escape
- **THEN** the panel closes without affecting the drawing session or capture schedule

#### Scenario: User repositions the panel
- **WHEN** the user drags the panel to a new screen position
- **THEN** the panel moves to and stays at the new position for the remainder of the session

#### Scenario: Panel opens at a legible default size
- **WHEN** the feedback panel is first shown
- **THEN** its default size SHALL be large enough to read a Full Critique response or view an overlay image without the user manually resizing the window first

#### Scenario: Long feedback text is scrollable
- **WHEN** a feedback response's text is longer than the visible height of the feedback text area
- **THEN** the text area SHALL show a scrollbar allowing the user to scroll through and read the full response

## ADDED Requirements

### Requirement: Feedback panel and its openers are labeled Feedback Management
The feedback panel's window title, the main window's toolbar button that opens it, and the system tray menu entry that opens it SHALL all read "Feedback Management".

#### Scenario: Panel window title
- **WHEN** the feedback panel is shown
- **THEN** its window title reads "Feedback Management"

#### Scenario: Toolbar and tray labels
- **WHEN** the user views the main window toolbar or opens the tray menu
- **THEN** the control that opens the feedback panel is labeled "Feedback Management"

### Requirement: Opening the feedback panel does not request feedback
Clicking the "Feedback Management" toolbar button or tray menu entry SHALL only show the feedback panel. It SHALL NOT, by itself, send a request to the LLM. A feedback request SHALL only be sent when the user explicitly triggers one — via the panel's "Request Feedback" button, the configured hotkey, or automatic stuck detection.

#### Scenario: Opening the panel with no prior history
- **WHEN** the user clicks "Feedback Management" and no feedback has been requested yet this session
- **THEN** the panel opens showing an idle/empty state and no LLM request is made

#### Scenario: Opening the panel with prior history
- **WHEN** the user clicks "Feedback Management" and feedback has previously been shown this session
- **THEN** the panel opens showing the most recently viewed feedback entry and no new LLM request is made

#### Scenario: Requesting feedback from the open panel
- **WHEN** the user clicks the panel's "Request Feedback" button
- **THEN** the system sends a feedback request using the currently selected mode, showing a loading state until the response arrives
