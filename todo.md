# Todo

All items have been converted to OpenSpec changes in `openspec/changes/`.

| Change | Description |
|--------|-------------|
| `session-management` | Session picker on launch, editable names, in-app switching |
| `history-frame-management` | Per-frame delete button, LLM lookback indicator |
| `feedback-history` | Feedback persistence, dedup, redesigned popup |
| `long-term-memory` | Cross-session observation store, prompt injection, viewer, progress panel |
| `log-config-on-startup` | DEBUG-level config dump on startup with secret redaction |
| `fix-pause-resume-initial-state` | Show "Start Capture" before window is selected |

Use `/op-custom-ready <change-name>` to load context, then `/op-custom-ship` to implement.
