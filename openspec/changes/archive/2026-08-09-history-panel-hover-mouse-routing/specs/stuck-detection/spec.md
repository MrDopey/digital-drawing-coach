## ADDED Requirements

### Requirement: At most one global hotkey listener exists at a time

Starting the hotkey listener SHALL stop any listener already running before creating a new one, so that repeated registration cannot leave an earlier listener running and unreachable.

This matters beyond tidiness on macOS, where each listener holds a system event tap and a run-loop thread: an orphaned listener's tap survives for the life of the process and cannot be removed, because the manager only tracks the most recently created listener.

Registering an empty hotkey SHALL stop any running listener and create none.

#### Scenario: Listener is started twice
- **WHEN** the hotkey listener is started while another listener is already running
- **THEN** the earlier listener SHALL be stopped, and exactly one listener SHALL remain

#### Scenario: Hotkey is set and then started
- **WHEN** the application sets a hotkey and then starts the manager, as it does during startup
- **THEN** only one listener SHALL be left running

#### Scenario: Hotkey is cleared
- **WHEN** the configured hotkey is set to an empty value
- **THEN** any running listener SHALL be stopped and no new listener SHALL be created
