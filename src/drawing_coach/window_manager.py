"""Cross-platform window enumeration and bounding-rect lookup.

Each backend implements list_windows() -> list[WindowInfo] and
get_window_rect(window_id) -> tuple[int,int,int,int] | None.
"""

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from typing import Protocol


@dataclass
class WindowInfo:
    id: int | str
    title: str
    app_name: str


class WindowBackend(Protocol):
    def list_windows(self) -> list[WindowInfo]: ...
    def get_window_rect(self, window_id: int | str) -> tuple[int, int, int, int] | None: ...


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
