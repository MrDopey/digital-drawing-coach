## ADDED Requirements

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
