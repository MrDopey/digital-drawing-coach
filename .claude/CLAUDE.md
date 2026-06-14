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
| Secrets | python-dotenv (`.env` in XDG config dir) |
| Tests | pytest, pytest-qt |
| Build | hatchling, PyInstaller |

## OpenSpec Workflow

This repo uses **OpenSpec** — a spec-driven change management system. Changes follow a structured lifecycle: explore → propose → implement → archive.

Use the project-specific skills for this repo:
- `/dc-propose` — propose a change with full worktree isolation (prevents orphaned `.openspec.yaml` files, names the worktree after the change)
- `/dc-ship` — implement, archive, sync specs, and merge the worktree into main