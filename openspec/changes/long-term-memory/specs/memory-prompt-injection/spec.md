## ADDED Requirements

### Requirement: Inject coach's notes into LLM system prompt
Before each LLM feedback request the system SHALL summarise recent observations from `MemoryStore` into a short "coach's notes" block and prepend it to the system prompt. The block SHALL include up to 20 recent observations and the total number of sessions the user has had (derived from `sessions_dir()`). The block SHALL be omitted when the memory store is empty.

#### Scenario: Memory store has observations
- **WHEN** a feedback request is made and the memory store contains at least one observation
- **THEN** the system prompt includes a coach's notes block before the base coaching prompt

#### Scenario: Memory store is empty
- **WHEN** a feedback request is made and the memory store has no observations
- **THEN** the system prompt does not include a coach's notes block and is identical to the prompt sent on first use

#### Scenario: Session count included in notes block
- **WHEN** the coach's notes block is generated
- **THEN** it includes a statement indicating how many sessions the user has had (e.g. "You have worked with this student across 5 sessions.")

#### Scenario: Notes block capped at 20 most recent observations
- **WHEN** the memory store has more than 20 observations
- **THEN** only the 20 most recent are included in the coach's notes block sent to the LLM
