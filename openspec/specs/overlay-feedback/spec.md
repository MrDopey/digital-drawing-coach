# overlay-feedback Specification

## Purpose
TBD - created by archiving change drawing-coach-enhancements. Update Purpose after archive.
## Requirements
### Requirement: LLM returns structured annotation data for overlay
When overlay mode is active, the system SHALL instruct the LLM to return a JSON annotation block alongside explanatory text. Annotations SHALL use normalised coordinates (0.0–1.0 relative to image dimensions) and support types: `arrow`, `line`, `circle`. The system SHALL parse this block and composite the annotations onto the screenshot using Pillow.

#### Scenario: LLM returns valid annotation JSON
- **WHEN** overlay mode is triggered and the LLM returns a response containing a valid JSON annotation block
- **THEN** the system parses the annotations, renders them onto a copy of the screenshot, and displays the annotated image in the feedback panel alongside the explanatory text

#### Scenario: LLM returns annotation with arrow type
- **WHEN** an annotation entry has `"type": "arrow"` with `from` and `to` coordinate pairs and an optional `label`
- **THEN** the system draws an arrow from the `from` point to the `to` point with the label text placed near the arrowhead

#### Scenario: LLM returns annotation with line type
- **WHEN** an annotation entry has `"type": "line"` with a `points` array of two or more coordinate pairs
- **THEN** the system draws a polyline through those points in the specified colour (default: red if omitted)

#### Scenario: LLM returns annotation with circle type
- **WHEN** an annotation entry has `"type": "circle"` with `center`, `radius`, and optional `label`
- **THEN** the system draws a circle outline at the specified position and radius, with the label placed above the circle

### Requirement: Overlay gracefully handles malformed annotation JSON
The system SHALL NOT crash or show an empty panel when the LLM response contains malformed or absent JSON. It SHALL fall back to displaying the plain text response and notify the user that the visual overlay could not be rendered.

#### Scenario: LLM returns no JSON block
- **WHEN** the LLM response in overlay mode contains no parseable JSON annotation block
- **THEN** the system displays the plain text response and shows a notice: "Visual overlay unavailable — showing text feedback instead"

#### Scenario: LLM returns malformed JSON
- **WHEN** the LLM response contains a JSON block that fails to parse or is missing required fields
- **THEN** the system logs the parse error, displays the text response, and shows the same fallback notice

### Requirement: Annotated image is saveable
The system SHALL allow the user to save the annotated screenshot to disk from the feedback panel.

#### Scenario: User saves annotated image
- **WHEN** the user clicks "Save Overlay" in the feedback panel while viewing an annotated image
- **THEN** the system saves the composited image as a PNG to a user-selected location and confirms with a success message

