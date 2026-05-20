## Context

The `digital-drawing-coach` change established the core pipeline: window capture → stuck detection → LLM feedback → panel display. This change builds on that foundation with four cross-cutting additions: a visual overlay feedback mode, style-aware prompting, disk-backed session history with deduplication/retention, and fully surfaced LLM errors. All parameters that were previously constants (`stuck_detector.py` thresholds, look-back frame count) move to the shared config layer.

## Goals / Non-Goals

**Goals:**
- Add overlay mode: LLM returns structured annotation data that Pillow composites onto the screenshot
- Inject user-selected drawing style/focus into every LLM system prompt
- Persist session frames to disk with duplicate dropping and configurable retention
- Surface copyright, rate-limit, and credit-exhaustion LLM error categories with clear UI messages
- Expose stuck-detection parameters and look-back frame count in the settings panel

**Non-Goals:**
- Real-time video annotation or live drawing tracing
- Storing LLM responses on disk (responses are session-local, frames are persisted)
- Automatically inferring drawing style from the screenshot (user-declared only)
- Syncing history to cloud storage

## Decisions

### Overlay annotation format: structured JSON from LLM

The LLM cannot reliably generate pixel-accurate PNGs. Instead, the overlay prompt instructs the LLM to return a JSON block alongside explanatory text:

```json
{
  "annotations": [
    {"type": "arrow", "from": [0.3, 0.5], "to": [0.45, 0.4], "label": "rotate arm up"},
    {"type": "line", "points": [[0.1, 0.8], [0.4, 0.6]], "color": "red"},
    {"type": "circle", "center": [0.6, 0.3], "radius": 0.05, "label": "foreshortening here"}
  ]
}
```

Coordinates are normalised (0–1) relative to image dimensions. Pillow draws these onto a copy of the screenshot. This is more reliable than asking the LLM to generate image data, and the JSON is parseable even if the LLM wraps it in prose.

Alternatives considered: ask LLM to return base64 annotated image — unreliable; use GPT-4o image generation — out of scope and expensive.

### Duplicate frame detection: reuse stuck-detection MAE

`capture_engine.py` already computes MAE between consecutive frames for stuck detection. We add a second, lower threshold (`dedup_threshold`, default: 2.0 MAE) checked before writing a new frame to disk. If the new frame is below this threshold against the last stored frame, it is silently dropped. This reuses existing infrastructure with no new dependency.

### Disk storage layout

```
~/.drawing-coach/
  sessions/
    2024-01-15_143022/          ← session directory (timestamp at start)
      meta.json                 ← {drawing_app, style_focus, start_time}
      frames/
        143022_001.png
        143045_002.png
        ...
  config.json
```

Sessions are written incrementally (each frame immediately on capture). On startup, sessions beyond the retention limit (default: last 10) are deleted oldest-first. No locking needed — only one app instance writes.

### History retention: count-based, not size-based

User configures "keep last N sessions" (default: 10). Size-based limits were considered but require background monitoring; count-based cleanup runs once at startup and is simple and predictable.

### Style/focus prompt injection

The selected style/focus string is stored in session state and injected as a dedicated section at the top of the system prompt:

```
You are a digital art coach. The user is currently practising: **anime/manga**.
Tailor all feedback to conventions and techniques specific to that style.
[rest of persona prompt]
```

For free-text focus (e.g. "gothic pokemon"), the same injection pattern applies. No sanitisation is needed beyond stripping leading/trailing whitespace — this text is only sent to the user's own LLM endpoint.

### LLM error classification

LiteLLM raises typed exceptions. We map them to user-facing messages:

| Exception | User message |
|---|---|
| `AuthenticationError` | "API key invalid or missing — check your LLM settings" |
| `RateLimitError` | "Rate limit reached — wait a moment and try again" |
| `InsufficientQuotaError` / `BudgetExceededError` | "Your API credits are exhausted — top up your account" |
| Content policy / copyright flag (response text contains policy refusal) | "The LLM flagged a content policy issue with this image — try a different feedback mode" |
| `NotFoundError` (model) | "Model not found — check the model name in your LLM settings" |
| Network / timeout | "Network error — check your connection and try again" |

Copyright/policy flags are not exceptions — they're refusal text in the response body. We detect them by checking for known refusal phrases ("I'm unable to", "I cannot", "content policy") and surface a distinct message rather than treating it as a successful response.

## Risks / Trade-offs

- **Overlay JSON parsing failures**: LLM may not always return well-formed JSON → Mitigation: wrap parse in try/except; fall back to displaying the text response without overlay and show a "Could not render overlay" notice
- **Disk space**: many sessions × many frames can grow large → Mitigation: retention limit + warn user in UI when session directory exceeds a configurable size threshold (default: 500 MB)
- **Style prompt injection changes output format**: some modes (Quick Hint) have strict length requirements that style context may push past → Mitigation: style injection is placed in system prompt, mode template is in user turn; LLM follows user-turn instructions more strictly for length
- **False copyright refusals**: real drawings occasionally trigger content policy (e.g. figure drawing) → Mitigation: user message explains what happened and suggests switching to text-only modes; no automatic retry
- **MAE dedup threshold too aggressive**: small but meaningful strokes dropped → Mitigation: dedup threshold is independently configurable from stuck-detection threshold; default set conservatively low (2.0 vs. stuck threshold of ~10.0)

## Migration Plan

These changes layer on top of `digital-drawing-coach` without breaking the existing interface:
1. Extend `config.json` schema with new fields (all have defaults — no migration needed for existing configs)
2. `capture_engine.py` storage layer switches from `deque` to disk; existing in-session history is unaffected if app restarts mid-session (frames already on disk are loaded back)
3. Settings panel gains new sections; existing settings are unchanged
