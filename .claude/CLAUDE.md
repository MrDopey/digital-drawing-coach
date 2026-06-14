# Drawing Coach — Claude Code Guide

## Project Overview

**Drawing Coach** is an AI-powered desktop app that watches a digital drawing session and delivers real-time coaching feedback via a vision LLM. It captures screenshots periodically, detects inactivity, and returns suggestions as text or as correction lines drawn directly onto the canvas.

Two runtime modes:
- **GUI mode** — PyQt6 desktop window with feedback panel, session history, and system tray icon

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| GUI | PyQt6, pynput |
| LLM | LiteLLM (supports OpenAI, Anthropic, Ollama, etc.) |
| Image processing | Pillow, mss, numpy |
| Config | `ConfigManager` (`config_manager.py`) — single load/save owner; merges `config.json`, `.env`, and env vars with explicit precedence |
| Secrets | python-dotenv (`.env` in XDG config dir) — API key only; written by `ConfigManager.save()` |
| Tests | pytest, pytest-qt |
| Build | hatchling, PyInstaller |

## OpenSpec Workflow

This repo uses **OpenSpec** — a spec-driven change management system. Changes follow a structured lifecycle: explore → propose → implement → archive.