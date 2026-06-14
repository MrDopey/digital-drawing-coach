## Context

The `HistoryPanel` (`src/drawing_coach/history_panel.py`) is a `QDialog` that shows captured frames as a grid of thumbnail icons in a `QListWidget`. Each frame is a `CapturedFrame` dataclass with an `image` (PIL `Image`) and an optional `path` (`Path | None`) pointing to the PNG saved on disk.

Currently, clicking a thumbnail selects it; nothing else happens. The interaction model is familiar from image gallery apps, but the current UI gives no feedback that the thumbnails are clickable beyond selection.

## Goals / Non-Goals

**Goals:**
- Double-clicking any thumbnail opens the image in the OS default viewer for PNG files
- Works cross-platform: Linux (`xdg-open` via `QDesktopServices`), macOS (`open`), Windows (`os.startfile`), all handled transparently by `QDesktopServices.openUrl`
- Frames without a disk path (in-memory only) are saved to a temp file before opening
- The affordance is surfaced with a status label ("Double-click to open")

**Non-Goals:**
- Single-click preview inside the panel (a future feature)
- Supporting formats other than PNG (all current frames are PNG)
- Managing the lifecycle of temp files beyond creating them (OS temp dir handles cleanup on reboot)

## Decisions

### Use `QDesktopServices.openUrl` instead of `subprocess`

`QDesktopServices.openUrl(QUrl.fromLocalFile(path))` is the canonical Qt cross-platform way to open a file with its registered default handler. It handles Linux/macOS/Windows without any `sys.platform` branching and is already available in PyQt6 — no new imports or dependencies.

**Alternatives considered:** `subprocess.run(["xdg-open", ...])` (Linux-only), `os.startfile` (Windows-only). Both require platform guards; `QDesktopServices` does not.

### Temp files for in-memory frames

`CapturedFrame.path` is `None` when the engine chose not to persist a frame (e.g., during first-run or a buffer-only scenario). To open such frames, save them to `tempfile.mkstemp(suffix=".png")` before calling `openUrl`. The temp file is created once per open action and not tracked — it persists until the OS clears the temp dir, which is acceptable for a single-session image review workflow.

### Attach frame data to `QListWidgetItem` via `setData`

Store the `CapturedFrame` on each `QListWidgetItem` using `item.setData(Qt.ItemDataRole.UserRole, frame)`. This avoids maintaining a parallel index list and makes the double-click handler self-contained.

## Risks / Trade-offs

- **No default viewer registered** → `QDesktopServices.openUrl` silently returns `False`. Risk is low on typical user machines; mitigation: show a `QMessageBox.warning` if the return value is `False`.
- **Temp file accumulation** → Files remain in the OS temp dir until system cleanup. Each is a single PNG (typically < 2 MB); not a practical concern for a drawing session.
- **Race on in-memory frame open** → If the same in-memory frame is opened rapidly, two temp files are created. No correctness issue; the viewer opens both. Acceptable.
