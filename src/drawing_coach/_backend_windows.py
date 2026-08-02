from __future__ import annotations

from typing import TYPE_CHECKING

from drawing_coach.window_manager import WindowInfo

if TYPE_CHECKING:
    from PIL import Image


class WindowsBackend:
    def list_windows(self) -> list[WindowInfo]:
        import psutil
        import win32gui
        import win32process

        results: list[WindowInfo] = []

        def _cb(hwnd: int, _: object) -> None:
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                app_name = psutil.Process(pid).name()
            except Exception:
                app_name = ""
            results.append(WindowInfo(id=hwnd, title=title, app_name=app_name))

        win32gui.EnumWindows(_cb, None)
        return results

    def get_window_rect(self, window_id: int | str) -> tuple[int, int, int, int] | None:
        import win32gui

        hwnd = int(window_id)
        if not win32gui.IsWindow(hwnd):
            return None
        rect = win32gui.GetWindowRect(hwnd)  # left, top, right, bottom
        left, top, right, bottom = rect
        return left, top, right - left, bottom - top

    def capture_image(self, window_id: int | str) -> Image.Image | None:
        import mss
        from PIL import Image

        rect = self.get_window_rect(window_id)
        if rect is None:
            return None
        left, top, width, height = rect
        if width <= 0 or height <= 0:
            return None

        with mss.mss() as sct:
            shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
            return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
