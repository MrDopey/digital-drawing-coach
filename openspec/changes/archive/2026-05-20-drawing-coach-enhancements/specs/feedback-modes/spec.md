## MODIFIED Requirements

### Requirement: Three selectable feedback modes
The system SHALL support four feedback modes that determine the depth and format of LLM coaching output. The active mode SHALL be selectable from the main UI and persist across the session.

Modes:
- **Quick Hint**: Single-sentence identification of the most pressing issue
- **Full Critique**: Structured breakdown covering composition, technique, anatomy/perspective, and suggested next steps
- **Practice Exercise**: A targeted drill or exercise based on the detected weakness
- **Overlay**: Visual annotation of the drawing with correction lines, arrows, and labels composited onto the screenshot

#### Scenario: User selects Quick Hint mode
- **WHEN** the user selects "Quick Hint" and feedback is triggered
- **THEN** the LLM response SHALL be a single sentence of no more than 30 words identifying the primary issue

#### Scenario: User selects Full Critique mode
- **WHEN** the user selects "Full Critique" and feedback is triggered
- **THEN** the LLM response SHALL be structured markdown with sections: Composition, Technique, Anatomy/Perspective, and Next Steps

#### Scenario: User selects Practice Exercise mode
- **WHEN** the user selects "Practice Exercise" and feedback is triggered
- **THEN** the LLM response SHALL describe a specific, actionable drawing exercise addressing the identified weakness

#### Scenario: User selects Overlay mode
- **WHEN** the user selects "Overlay" and feedback is triggered
- **THEN** the system sends the overlay annotation prompt to the LLM and renders the returned annotations on the screenshot as described in the overlay-feedback spec

#### Scenario: Mode persists within session
- **WHEN** the user selects a feedback mode and triggers multiple feedback requests
- **THEN** all subsequent requests in the session SHALL use the selected mode until changed
