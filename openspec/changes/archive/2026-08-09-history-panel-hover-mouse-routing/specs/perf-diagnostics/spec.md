## ADDED Requirements

### Requirement: An application-wide input probe reports mouse-event delivery

When instrumentation is enabled, the system SHALL count every mouse event the process receives via an application-level event filter, independently of which widget the event is routed to, and report per aggregation window: the count per event type, the widget types that mouse moves were delivered to, and the application's active-window and focus state.

Comparing this application-wide count against a widget-level probe distinguishes three otherwise indistinguishable cases: events never reaching the process, events reaching the process but not being routed to the intended widget, and events arriving normally so that the delay lies elsewhere.

The active-window and focus state SHALL be sampled on the GUI thread, because the flush runs on the watchdog thread and must not touch Qt objects.

#### Scenario: Mouse events are counted application-wide
- **WHEN** mouse events are delivered anywhere in the application with instrumentation enabled
- **THEN** a `PERF-INPUT` line reports the count per event type for the window

#### Scenario: Move receivers are identified
- **WHEN** mouse moves are delivered during an aggregation window
- **THEN** the report names the widget types that received them, ranked by count, so a move landing on an unintended widget is visible

#### Scenario: Window state accompanies the counts
- **WHEN** an input report is emitted
- **THEN** it carries the application state and the active window and focus widget observed on the GUI thread

#### Scenario: Instrumentation is disabled
- **WHEN** instrumentation is not enabled
- **THEN** no application-level event filter is installed and no `PERF-INPUT` lines are emitted

#### Scenario: No input occurred in a window
- **WHEN** an aggregation window passes with no mouse events
- **THEN** no `PERF-INPUT` line is emitted for that window
