from __future__ import annotations

from drawing_coach.window_manager import WindowInfo


class WindowsBackend:
    def list_windows(self) -> list[WindowInfo]:
        import win32gui
        import win32process
        import psutil

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
