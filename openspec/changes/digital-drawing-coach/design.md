## Context

There is no existing codebase — this is a greenfield desktop application. The app runs alongside the user's drawing software, captures the drawing window periodically, and delivers LLM-powered coaching. Key constraints: cross-platform (macOS/Windows/Linux), non-intrusive UX (the user is focused on drawing, not our app), and flexibility to use any vision-capable LLM the user already has access to.

## Goals / Non-Goals

**Goals:**
- Capture screenshots of a user-selected drawing window at a configurable interval
- Detect "stuck" state via pixel-change heuristics or hotkey
- Send screenshots to a vision LLM (via LiteLLM) and display feedback
- Support multiple feedback modes (quick hint, full critique, practice exercise)
- Allow full LLM configuration (provider, model, API key, base URL)
- Store session history of captures in memory (not persisted across sessions by default)

**Non-Goals:**
- Providing drawing content itself (brushes, layers, tools) — we sit alongside drawing apps
- Cloud sync or persistent drawing history
- Video recording or full screen capture
- Real-time streaming feedback (feedback is triggered, not continuous)
- Integrating with drawing app APIs (we use screen capture only)

## Decisions

### Language & Runtime: Python

Python chosen over Electron/Node for its mature cross-platform screenshot (`mss`), hotkey (`pynput`), and image processing (`Pillow`) libraries. LiteLLM is a Python library, eliminating a bridge layer.

Alternatives: Electron + Node — better UI flexibility but requires subprocess bridge to Python for LiteLLM and screenshots; adds packaging complexity.

### UI Framework: PyQt6 (or PySide6)

PyQt6 provides a system-tray icon, floating overlay panel, and native-looking widgets across all platforms. `tkinter` was considered but lacks system tray and modern styling. Web-based (Electron wrapper) adds bundle size and complexity.

### Screenshot Backend: mss

`mss` is faster than `Pillow`'s `ImageGrab` and works on all platforms including Wayland (with fallback). Captures a specific window by bounding rect obtained from the window manager.

### Window Detection: per-platform APIs

- **Windows**: `pywin32` (`win32gui`) to enumerate windows and get bounding rect
- **macOS**: `AppKit`/`Quartz` via `pyobjc` for window list
- **Linux**: `xdotool` / `xlib` for X11; Wayland via portal API fallback

A thin `window_manager.py` abstraction wraps all three.

### Stuck Detection Heuristics

Compare consecutive screenshots using mean absolute pixel difference (MAE via numpy). If MAE falls below a configurable threshold for N consecutive intervals, trigger stuck state. This avoids false positives from minor brush strokes while catching genuine stalls.

### LLM Integration: LiteLLM

LiteLLM provides a unified `completion()` API that supports OpenAI, Anthropic, Ollama, and hundreds of other providers via a single interface. Users supply `model`, `api_key`, and optionally `api_base` for custom endpoints.

Prompt engineering: system prompt establishes the "digital art coach" persona with knowledge of perspective, anatomy, color theory, and technique. The user screenshot is passed as a base64 image in the message.

### Feedback Modes

Three structured prompt templates:
1. **Quick hint** — one sentence, most pressing issue only
2. **Full critique** — structured markdown: composition, technique, anatomy/perspective, next steps
3. **Practice exercise** — a targeted drill based on the detected weakness

Mode is selectable from the UI; the template is injected into the system prompt.

### Data Flow

```
[Drawing App Window]
        ↓ (mss capture, every N seconds)
[Screenshot Buffer] ← ring buffer, last M frames
        ↓ (on trigger: heuristic or hotkey)
[Feedback Engine]
  - selects frames (latest + 2 history frames)
  - builds LiteLLM messages with base64 images
  - calls LLM
        ↓
[Feedback Panel / Overlay]
  - displays markdown-rendered response
```

## Risks / Trade-offs

- **Window capture permission (macOS)**: Screen recording permission required; first-run prompt may confuse users → Mitigation: clear onboarding step with system settings link
- **LLM cost/latency**: Vision calls are more expensive and slower than text → Mitigation: stuck detection rate-limits calls; quick hint mode is cheapest
- **Pixel heuristic false positives**: Zooming or panning triggers high MAE without real drawing progress → Mitigation: configurable threshold + user can always dismiss or retrigger manually
- **Wayland window capture**: Limited window-specific capture on Wayland → Mitigation: fall back to full screen capture with user-guided crop rect; document limitation
- **LiteLLM model support varies**: Not all models support vision input → Mitigation: warn at config time if selected model is not vision-capable (check LiteLLM model info)
