## ADDED Requirements

### Requirement: Three selectable feedback modes
The system SHALL support three feedback modes that determine the depth and format of LLM coaching output. The active mode SHALL be selectable from the main UI and persist across the session.

Modes:
- **Quick Hint**: Single-sentence identification of the most pressing issue
- **Full Critique**: Structured breakdown covering composition, technique, anatomy/perspective, and suggested next steps
- **Practice Exercise**: A targeted drill or exercise based on the detected weakness

#### Scenario: User selects Quick Hint mode
- **WHEN** the user selects "Quick Hint" and feedback is triggered
- **THEN** the LLM response SHALL be a single sentence of no more than 30 words identifying the primary issue

#### Scenario: User selects Full Critique mode
- **WHEN** the user selects "Full Critique" and feedback is triggered
- **THEN** the LLM response SHALL be structured markdown with sections: Composition, Technique, Anatomy/Perspective, and Next Steps

#### Scenario: User selects Practice Exercise mode
- **WHEN** the user selects "Practice Exercise" and feedback is triggered
- **THEN** the LLM response SHALL describe a specific, actionable drawing exercise addressing the identified weakness

#### Scenario: Mode persists within session
- **WHEN** the user selects a feedback mode and triggers multiple feedback requests
- **THEN** all subsequent requests in the session SHALL use the selected mode until changed

### Requirement: Feedback is displayed in a non-intrusive panel
The system SHALL display feedback in a panel that does not obscure the drawing application. The panel SHALL be dismissible and repositionable by the user.

#### Scenario: Feedback panel appears after response
- **WHEN** the LLM returns a response
- **THEN** the feedback panel becomes visible with the rendered markdown content

#### Scenario: User dismisses feedback panel
- **WHEN** the user clicks the dismiss button or presses Escape
- **THEN** the panel closes without affecting the drawing session or capture schedule

#### Scenario: User repositions the panel
- **WHEN** the user drags the panel to a new screen position
- **THEN** the panel moves to and stays at the new position for the remainder of the session

### Requirement: Feedback history is accessible within the session
The system SHALL retain all feedback responses from the current session and allow the user to review previous responses.

#### Scenario: User opens feedback history
- **WHEN** the user clicks "Previous Feedback" in the panel
- **THEN** the system displays a scrollable list of previous feedback items with timestamps and the mode used
