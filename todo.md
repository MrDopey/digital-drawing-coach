# Todo

## Known Issues to Address

- [ ] **Silent write failure in `CaptureEngine._write_frame`** (`src/drawing_coach/capture_engine.py:248-251`): exceptions during `img.save()` are caught and swallowed; the frame is added to the buffer with `path=None` and no log, warning, or callback is emitted. Verify failure is surfaced (log at minimum, ideally `on_frame_captured` or a dedicated error callback).
