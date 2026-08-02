## ADDED Requirements

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
