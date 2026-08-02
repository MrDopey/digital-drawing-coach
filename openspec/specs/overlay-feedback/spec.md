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

### Requirement: Annotations are rendered onto the same frame the LLM was shown
When overlay mode is active, the system SHALL ensure the LLM's annotation coordinates and the image they are composited onto always refer to the same single screenshot. The system SHALL NOT send multiple screenshots to the LLM for annotation purposes, since annotation coordinates are normalised relative to a single image and there is no mechanism for the LLM to disambiguate which of several images its coordinates describe.

#### Scenario: Canvas has scrolled or panned since an earlier capture
- **WHEN** overlay mode is triggered and the drawing canvas has scrolled or changed since previous captures were taken
- **THEN** the annotations returned by the LLM describe only content visible in the single screenshot that was sent, so rendered arrows, lines, and circles always correspond to features actually present in the displayed image

#### Scenario: Overlay annotations never reference stale content
- **WHEN** the annotated image is displayed in the feedback panel
- **THEN** every annotation's coordinates fall on content that was visible in the exact screenshot the LLM analysed, with no annotations left over from a different, prior capture

### Requirement: Annotation labels remain legible against any underlying content
The system SHALL render a background behind every annotation label's text, sized to the text's bounding box. The label text color and its background color SHALL be a fixed, preselected pair, independent of the annotation's own line/arrow/circle color — the system SHALL NOT compute the label's colors dynamically from the annotation's color or the underlying image. This SHALL apply to both `arrow` and `circle` annotation labels.

#### Scenario: Label color is similar to the underlying drawing
- **WHEN** an annotation's stroke color closely matches the color of the drawing content directly beneath its label
- **THEN** the label remains readable because its fixed background/text color pair contrasts with the underlying content regardless of the annotation's own stroke color

#### Scenario: Label rendering is independent of annotation color
- **WHEN** annotations of different colors (e.g. "red", "blue", "white", "black") each include a label
- **THEN** every label's text and background use the same fixed, preselected color pair, regardless of that annotation's own stroke color

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

### Requirement: Overlay and feedback text share a user-resizable split view
When a feedback response includes an annotated overlay image, the feedback panel SHALL display the overlay image in a top section and the full feedback text in a bottom section simultaneously, divided by a draggable splitter. The user SHALL be able to drag the splitter to resize either section. When the current feedback entry has no overlay image, the top section SHALL be collapsed so only the feedback text is shown.

#### Scenario: Overlay response shows both sections
- **WHEN** a feedback response includes an annotated overlay image
- **THEN** the panel shows the overlay image in the top section and the full response text in the bottom section, with a draggable divider between them

#### Scenario: User resizes the split
- **WHEN** the user drags the divider between the overlay section and the feedback text section
- **THEN** the two sections resize accordingly, and both remain usable (neither is reduced to an unusable size)

#### Scenario: Text-only response collapses the overlay section
- **WHEN** the current feedback entry has no overlay image (e.g. Quick Hint, Full Critique, or Practice Exercise mode)
- **THEN** the overlay section is collapsed and the feedback text section fills the available space

### Requirement: Overlay image is viewable at full detail via scrolling
The overlay section SHALL display the annotated image inside a scrollable area rather than force-scaling it down to fit the available space, so annotation detail is not lost when the section is smaller than the image.

#### Scenario: Overlay image larger than the visible section
- **WHEN** the annotated overlay image is larger than the current height/width of the overlay section
- **THEN** the section shows scrollbars allowing the user to pan and view the full image at full detail

### Requirement: Overlay image is zoomable
The overlay section SHALL let the user zoom the annotated image in and out independently of the overlay/feedback split, via zoom-in, zoom-out, and reset-zoom controls. Zooming in SHALL render the image larger (panned via the scrollable overlay section); zooming out SHALL render it smaller. The zoom level SHALL reset to its default whenever the user navigates to a different feedback history entry.

#### Scenario: User zooms in
- **WHEN** the user activates the zoom-in control (or zooms in via `Ctrl+Wheel` over the image) while viewing an overlay image
- **THEN** the image renders larger, and the overlay section's scrollbars update to let the user pan to any part of the enlarged image

#### Scenario: User zooms out
- **WHEN** the user activates the zoom-out control (or zooms out via `Ctrl+Wheel` over the image) while viewing an overlay image
- **THEN** the image renders smaller, down to a minimum zoom level below which it will not shrink further

#### Scenario: User resets zoom
- **WHEN** the user activates the reset-zoom control
- **THEN** the image returns to its default (native) display size

#### Scenario: Zoom resets on navigation
- **WHEN** the user has zoomed the current overlay image and then navigates to the previous or next feedback history entry
- **THEN** the newly displayed entry's overlay image (if any) is shown at the default zoom level, not the previous entry's zoom level

