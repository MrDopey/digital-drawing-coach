"""Cross-platform window enumeration and bounding-rect lookup.

Each backend implements list_windows() -> list[WindowInfo],
get_window_rect(window_id) -> tuple[int,int,int,int] | None, and
capture_image(window_id) -> PIL.Image.Image | None.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from PIL import Image


@dataclass
class WindowInfo:
    id: int | str
    title: str
    app_name: str


class WindowBackend(Protocol):
    def list_windows(self) -> list[WindowInfo]: ...
    def get_window_rect(
        self, window_id: int | str
    ) -> tuple[int, int, int, int] | None: ...
    def capture_image(self, window_id: int | str) -> Image.Image | None: ...


def _make_backend() -> WindowBackend:
    system = platform.system()
    if system == "Windows":
        from drawing_coach._backend_windows import WindowsBackend

        return WindowsBackend()
    elif system == "Darwin":
        from drawing_coach._backend_macos import MacOSBackend

        return MacOSBackend()
    else:
        from drawing_coach._backend_linux import LinuxBackend

        return LinuxBackend()


class WindowManager:
    """Thin facade over the platform-specific backend."""

    def __init__(self) -> None:
        self._backend = _make_backend()

    def list_windows(self) -> list[WindowInfo]:
        return self._backend.list_windows()

    def get_window_rect(self, window_id: int | str) -> tuple[int, int, int, int] | None:
        """Return (left, top, width, height) or None if the window is gone."""
        return self._backend.get_window_rect(window_id)

    def capture_image(self, window_id: int | str) -> Image.Image | None:
        """Return a screenshot of just the given window, or None if unavailable."""
        return self._backend.capture_image(window_id)
