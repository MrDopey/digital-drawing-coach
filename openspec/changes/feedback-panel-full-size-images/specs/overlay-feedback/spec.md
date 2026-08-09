## MODIFIED Requirements

### Requirement: Overlay and feedback text share a user-resizable split view
When a feedback entry has an image to display — a composited annotated overlay image, or the full-resolution captured frame the feedback was based on — the feedback panel SHALL display that image in a top section and the full feedback text in a bottom section simultaneously, divided by a draggable splitter. The user SHALL be able to drag the splitter to resize either section. When the current feedback entry has no image of any kind, the top section SHALL be collapsed so only the feedback text is shown.

#### Scenario: Overlay response shows both sections
- **WHEN** a feedback response includes an annotated overlay image
- **THEN** the panel shows the overlay image in the top section and the full response text in the bottom section, with a draggable divider between them

#### Scenario: Non-overlay response also shows both sections
- **WHEN** a Quick Hint, Full Critique, or Practice Exercise entry has a resolvable full-resolution captured frame
- **THEN** the panel shows that frame in the top section and the full response text in the bottom section, with a draggable divider between them

#### Scenario: User resizes the split
- **WHEN** the user drags the divider between the image section and the feedback text section
- **THEN** the two sections resize accordingly, and both remain usable (neither is reduced to an unusable size)

#### Scenario: Response with no image collapses the image section
- **WHEN** the current feedback entry has neither a composited overlay image nor a resolvable full-resolution frame
- **THEN** the image section is collapsed and the feedback text section fills the available space

### Requirement: Overlay image is viewable at full detail via scrolling
The image section SHALL display the image it is showing — a composited annotated overlay image or a full-resolution captured frame — inside a scrollable area rather than force-scaling it down to fit the available space, so detail is not lost when the section is smaller than the image.

#### Scenario: Image larger than the visible section
- **WHEN** the displayed image is larger than the current height/width of the image section
- **THEN** the section shows scrollbars allowing the user to pan and view the full image at full detail

### Requirement: Overlay image is zoomable
The image section SHALL let the user zoom the image it is showing — a composited annotated overlay image or a full-resolution captured frame — in and out independently of the image/feedback split, via zoom-in, zoom-out, and reset-zoom controls. Zooming in SHALL render the image larger (panned via the scrollable image section); zooming out SHALL render it smaller. The zoom level SHALL reset to its default whenever the user navigates to a different feedback history entry.

#### Scenario: User zooms in
- **WHEN** the user activates the zoom-in control (or zooms in via `Ctrl+Wheel` over the image) while viewing any feedback image
- **THEN** the image renders larger, and the image section's scrollbars update to let the user pan to any part of the enlarged image

#### Scenario: User zooms out
- **WHEN** the user activates the zoom-out control (or zooms out via `Ctrl+Wheel` over the image) while viewing any feedback image
- **THEN** the image renders smaller, down to a minimum zoom level below which it will not shrink further

#### Scenario: User resets zoom
- **WHEN** the user activates the reset-zoom control
- **THEN** the image returns to its default (native) display size

#### Scenario: Zoom resets on navigation
- **WHEN** the user has zoomed the current image and then navigates to the previous or next feedback history entry
- **THEN** the newly displayed entry's image (if any) is shown at the default zoom level, not the previous entry's zoom level
