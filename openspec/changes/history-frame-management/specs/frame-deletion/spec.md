## ADDED Requirements

### Requirement: Per-frame delete button in history panel
Each frame thumbnail in the history panel SHALL display a delete button that is only visible when the user hovers over that thumbnail. Activating the delete button SHALL remove the frame from the in-memory capture buffer immediately so it will not be included in subsequent LLM requests. The frame file on disk SHALL NOT be deleted.

#### Scenario: Delete button appears on hover
- **WHEN** the user moves the mouse pointer over a frame thumbnail in the history panel
- **THEN** a delete/dismiss button (e.g. "×") becomes visible on that thumbnail

#### Scenario: Delete button hides when not hovering
- **WHEN** the user moves the mouse pointer away from a thumbnail
- **THEN** the delete button is hidden

#### Scenario: User deletes a frame
- **WHEN** the user clicks the delete button on a frame thumbnail
- **THEN** that frame is removed from the in-memory buffer, the thumbnail is removed from the history panel, and the lookback indicator updates to reflect the new buffer state

#### Scenario: Deleted frame is excluded from LLM request
- **WHEN** a frame has been deleted from the buffer and the user requests LLM feedback
- **THEN** the deleted frame is not included in the images sent to the LLM

#### Scenario: Deleted frame's file remains on disk
- **WHEN** a frame is deleted from the buffer via the history panel
- **THEN** the corresponding PNG file in the session's `frames/` directory is not removed from disk
