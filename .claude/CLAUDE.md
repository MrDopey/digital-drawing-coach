# Drawing Coach — Claude Code Guide

## Project Overview

**Drawing Coach** is an AI-powered desktop app that watches a digital drawing session and delivers real-time coaching feedback via a vision LLM. It captures screenshots periodically, detects inactivity, and returns suggestions as text or as correction lines drawn directly onto the canvas.

Two runtime modes:
- **GUI mode** — PyQt6 desktop window with feedback panel, session history, and system tray icon

## UI Conventions (PyQt6)

Dialogs must be resizable: content reflows correctly when the user drags the window edge.

- Expanding widgets need a stretch factor: `layout.addWidget(w, 1)` — without it they don't grow when the dialog is resized
- Word-wrapped `QLabel`s in grid layouts need `setMinimumWidth(1)` — without it they lock the minimum layout width
- Selectable `QLabel`s need `setTextInteractionFlags(TextSelectableByMouse | TextSelectableByKeyboard)` — without it users cannot copy displayed text
- Scrollable content: `QScrollArea(setWidgetResizable=True, frameShape=NoFrame)`; no hardcoded dialog heights
- Child dialogs opened from a modal parent must use `exec()` not `show()` — `show()` inside an `exec()` loop cannot receive focus

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| GUI | PyQt6, pynput |
| LLM | LiteLLM (supports OpenAI, Anthropic, Ollama, etc.) |
| Image processing | Pillow, mss (Windows/Linux window capture), numpy |
| Window capture | `WindowBackend.capture_image()` (`window_manager.py`) — Windows/Linux use `mss.grab()` on the window rect; **macOS uses direct CoreGraphics** (`_backend_macos.py`, `CGWindowListCreateImage` scoped to the window ID) instead of `mss`, because `mss`'s macOS backend captures a screen *region* (compositing whatever else is on-screen there) rather than one window's content |
| Config | `ConfigManager` (`config_manager.py`) — single load/save owner; merges `config.json`, `.env`, and env vars with explicit precedence |
| Secrets | python-dotenv (`.env` in XDG config dir) — API key only; written by `ConfigManager.save()` |
| Long-term memory | `MemoryStore` (`memory_store.py`) — `memory.json` (raw cross-session drawing observations) and `memory_summaries.json` (their periodic re-summarisation history); this is app data feeding the coaching LLM's prompt, unrelated to and separate from Claude Code's own memory/auto-memory system |
| Tests | pytest, pytest-qt |
| Build | hatchling, PyInstaller |
