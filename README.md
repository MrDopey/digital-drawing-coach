# Drawing Coach

An AI-powered desktop app that watches your digital drawing session and gives real-time coaching feedback.

## Features

- Captures screenshots of any drawing application periodically
- Detects when you're stuck (low pixel change) or responds to a manual hotkey
- Sends screenshots to a vision LLM and returns targeted drawing feedback
- Three feedback modes: Quick Hint, Full Critique, Practice Exercise
- Works with any LLM via [LiteLLM](https://docs.litellm.ai/) — OpenAI, Anthropic, Ollama, and more
- Session history timeline, system tray icon, draggable feedback panel

## Requirements

- Python 3.11+
- A vision-capable LLM API key (e.g. OpenAI `gpt-4o`, Anthropic `claude-3-5-sonnet-20241022`, or a local Ollama model like `ollama/llava`)

## Installation

### Pre-built binaries (recommended)

Download the latest release for your platform from the [GitHub Releases](../../releases/latest) page:

| Platform | File |
|---|---|
| Windows | `drawing-coach-<version>-windows.zip` (~70 MB) |
| macOS | `drawing-coach-<version>-macos.zip` (~90 MB, arm64 + x86_64) |
| Linux | `drawing-coach-<version>-linux.zip` (~65 MB) |

Unzip and run the `drawing-coach` executable inside.

> **macOS**: On first launch, right-click → Open to bypass Gatekeeper.  
> Then grant **Screen Recording** permission in  
> **System Settings → Privacy & Security → Screen Recording**,  
> and **Accessibility** permission if the global hotkey is needed.

> **Linux**: You may need `xdotool` installed (`apt install xdotool`) for window detection.

### Install from source

```bash
git clone <repo>
cd drawing-coach

# GUI desktop app
pip install -e ".[gui]"

# macOS — also install pyobjc bindings
pip install -e ".[gui,macos]"

# Windows — also install pywin32
pip install -e ".[gui,windows]"
```

## Running

```bash
python -m drawing_coach
# or, after pip install:
drawing-coach
```

On first launch, the onboarding dialog will guide you through:
1. Configuring your LLM (model name + API key)
2. Selecting your drawing application window
3. Starting automatic capture

## Docker (headless / server mode)

The Docker image runs Drawing Coach as a headless HTTP API server — no GUI required.
Useful for automated testing, CI feedback pipelines, or integrating with other tools.

```bash
docker run -d \
  -p 8080:8080 \
  -e DRAWING_COACH_MODEL=gpt-4o \
  -e DRAWING_COACH_API_KEY=sk-... \
  ghcr.io/<owner>/drawing-coach:latest
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `DRAWING_COACH_MODEL` | *(required)* | LiteLLM model identifier (e.g. `gpt-4o`, `claude-3-5-sonnet-20241022`) |
| `DRAWING_COACH_API_KEY` | *(required)* | API key for the chosen provider |
| `DRAWING_COACH_API_BASE` | *(blank)* | Override API base URL (for local Ollama, LiteLLM proxy, etc.) |
| `DRAWING_COACH_PORT` | `8080` | Port the HTTP server listens on |
| `DRAWING_COACH_HEADLESS` | `1` (always set in image) | Set to `1` to start in headless mode outside Docker |

## API Reference

When running in headless mode, a FastAPI server starts on port 8080.  
Interactive docs are available at `http://localhost:8080/docs`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Returns `{"status": "ok", "version": "..."}` |
| `POST` | `/capture` | Trigger a single screenshot capture |
| `POST` | `/feedback` | Request LLM feedback; optional body `{"mode": "quick_hint\|full_critique\|overlay\|practice_exercise"}` |
| `GET` | `/config` | Return current config (api_key excluded) |
| `PUT` | `/config` | Update config fields (model, api_base, custom_instructions, lookback_frames, style_focus) |

Example:

```bash
# Health check
curl http://localhost:8080/health

# Trigger feedback
curl -X POST http://localhost:8080/feedback \
  -H "Content-Type: application/json" \
  -d '{"mode": "quick_hint"}'
```

## LLM Configuration Examples

| Provider | Model | API Key | Base URL |
|---|---|---|---|
| OpenAI | `gpt-4o` | `sk-...` | *(leave blank)* |
| Anthropic | `claude-3-5-sonnet-20241022` | `sk-ant-...` | *(leave blank)* |
| Ollama (local) | `ollama/llava` | *(leave blank)* | `http://localhost:11434` |
| LiteLLM proxy | `openai/gpt-4o` | your proxy key | `http://localhost:4000` |

## Hotkey

Default: **Ctrl+Shift+F** — press any time to get immediate feedback.  
Configurable in Settings → Capture tab.

## Development

```bash
pip install -e ".[dev]"
pytest
```
