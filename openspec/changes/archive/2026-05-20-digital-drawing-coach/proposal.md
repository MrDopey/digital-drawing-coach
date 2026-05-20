## Why

Digital art learners lack real-time, contextual feedback while practicing — they either wait for instructor reviews or rely on generic tutorials that don't respond to what they're actually drawing. This app closes that gap by watching the user draw and surfacing targeted coaching when they need it most.

## What Changes

- New desktop application that runs alongside any drawing software (Paint, Krita, Procreate via screen share, etc.)
- Periodic screenshot capture builds a timeline of the drawing session for progress tracking and LLM context
- Stuck detection triggers coaching automatically (via heuristic analysis of drawing inactivity/low change) or manually via a configurable hotkey
- Screenshots are sent to a vision-capable LLM which returns targeted, art-specific suggestions (anatomical issues, perspective problems, technique tips)
- Multiple feedback modes: concise text hints, detailed critique, or practice exercise recommendations
- User-configurable LLM backend via LiteLLM — supports OpenAI, Anthropic, local models, or any compatible endpoint

## Capabilities

### New Capabilities

- `app-selection`: User selects and registers the target drawing application; the app monitors that window for screenshots
- `screenshot-capture`: Periodic screenshot capture of the drawing window with configurable interval; maintains a session history of captures
- `stuck-detection`: Detects when the user is stuck — either via automated heuristics (low pixel change over time, inactivity) or user-triggered hotkey
- `llm-feedback`: Sends current screenshot (and optionally recent history frames) to a vision LLM and returns structured drawing feedback
- `feedback-modes`: Configurable output modes — quick hint, full critique, or practice exercise — presented in a non-intrusive overlay or side panel
- `llm-config`: User-facing configuration for LLM provider, model name, API key, and base URL (LiteLLM compatible)

### Modified Capabilities

## Impact

- New standalone desktop application (Python recommended for cross-platform screenshot and hotkey support)
- Dependencies: screenshot library (e.g. `mss` or `Pillow`), hotkey listener (e.g. `pynput` or `keyboard`), LiteLLM for model routing, a UI framework (e.g. `tkinter`, `PyQt`, or `Electron` via packaging)
- Requires user's LLM API credentials; no data stored externally beyond what the chosen LLM provider receives
- Cross-platform target: macOS, Windows, Linux
