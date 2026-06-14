## MODIFIED Requirements

### Requirement: LLM feedback uses art-coaching persona
The system SHALL include a system prompt that establishes the LLM as a knowledgeable digital art coach with expertise in perspective, anatomy, color theory, and technique. The persona SHALL remain consistent across all feedback modes. When a non-empty coach's notes block is provided (from the memory store), it SHALL be prepended to the system prompt before the base coaching persona text. The system prompt SHALL also instruct the LLM to optionally append a `<!-- observations: [...] -->` HTML comment containing a JSON array of `{category, note}` objects derived from the current response, to enable future memory accumulation.

#### Scenario: System prompt is sent with every request
- **WHEN** any feedback request is made
- **THEN** the art-coaching system prompt SHALL be prepended to the LiteLLM messages array

#### Scenario: User's custom instructions are respected
- **WHEN** the user has added custom coaching instructions in settings
- **THEN** those instructions SHALL be appended to the system prompt for every request

#### Scenario: Coach's notes block injected when memory is non-empty
- **WHEN** a feedback request is made and the memory store contains observations
- **THEN** the coach's notes block is prepended to the system prompt before the base persona text

#### Scenario: Coach's notes block omitted when memory is empty
- **WHEN** a feedback request is made and the memory store has no observations
- **THEN** the system prompt is assembled without a coach's notes block

#### Scenario: LLM instructed to emit observations comment
- **WHEN** any feedback request is made
- **THEN** the system prompt includes an instruction asking the LLM to append a `<!-- observations: [...] -->` comment with structured observations from its response
