## MODIFIED Requirements

### Requirement: Three selectable feedback modes
The system SHALL support four feedback modes that determine the depth and format of LLM coaching output. The active mode SHALL be presented as a horizontal strip of radio buttons — one per mode, all visible simultaneously — in the feedback panel, and SHALL persist across the session. The same row SHALL include a right-aligned button that triggers a feedback request using the currently selected mode.

Modes:
- **Quick Hint**: Single-sentence identification of the most pressing issue
- **Full Critique**: Structured breakdown covering composition, technique, anatomy/perspective, and suggested next steps
- **Practice Exercise**: A targeted drill or exercise based on the detected weakness
- **Overlay**: Visual annotation of the drawing with correction lines, arrows, and labels composited onto the screenshot

#### Scenario: User selects Quick Hint mode
- **WHEN** the user selects the "Quick Hint" radio button and feedback is triggered
- **THEN** the LLM response SHALL be a single sentence of no more than 30 words identifying the primary issue

#### Scenario: User selects Full Critique mode
- **WHEN** the user selects the "Full Critique" radio button and feedback is triggered
- **THEN** the LLM response SHALL be structured markdown with sections: Composition, Technique, Anatomy/Perspective, and Next Steps

#### Scenario: User selects Practice Exercise mode
- **WHEN** the user selects the "Practice Exercise" radio button and feedback is triggered
- **THEN** the LLM response SHALL describe a specific, actionable drawing exercise addressing the identified weakness

#### Scenario: User selects Overlay mode
- **WHEN** the user selects the "Overlay" radio button and feedback is triggered
- **THEN** the system sends the overlay annotation prompt to the LLM and renders the returned annotations on the screenshot as described in the overlay-feedback spec

#### Scenario: Mode persists within session
- **WHEN** the user selects a feedback mode radio button and triggers multiple feedback requests
- **THEN** all subsequent requests in the session SHALL use the selected mode until changed

#### Scenario: User triggers feedback from the panel
- **WHEN** the user clicks the right-aligned trigger button in the mode row
- **THEN** the system requests feedback using the currently selected mode, identically to triggering feedback via the main window button, tray menu, or hotkey

### Requirement: Feedback is displayed in a non-intrusive panel
The system SHALL display feedback in a panel that does not obscure the drawing application. The panel SHALL be dismissible and repositionable by the user. The panel SHALL open at a default size large enough to display both a full-length text response and a full overlay image without requiring the user to resize it first. The panel's content area SHALL be responsive: when the user resizes the panel, an overlay image currently on display SHALL rescale to fit the new content area while preserving its aspect ratio.

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

#### Scenario: Overlay image rescales when the panel is resized
- **WHEN** an overlay image is currently displayed and the user resizes the feedback panel
- **THEN** the displayed image SHALL be rescaled to fit the new content area, preserving its aspect ratio, without requiring the user to navigate away from and back to that feedback item

### Requirement: Feedback history is accessible within the session
The system SHALL retain all feedback responses from the current session and allow the user to review previous responses.

#### Scenario: User opens feedback history
- **WHEN** the user clicks "Previous Feedback" in the panel
- **THEN** the system displays a scrollable list of previous feedback items with timestamps and the mode used
