from __future__ import annotations

from drawing_coach.window_manager import WindowInfo


class MacOSBackend:
    def list_windows(self) -> list[WindowInfo]:
        import Quartz

        options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
        win_list = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)

        results: list[WindowInfo] = []
        for win in win_list:
            title = win.get("kCGWindowName", "") or ""
            app_name = win.get("kCGWindowOwnerName", "") or ""
            wid = win.get("kCGWindowNumber", 0)
            if not title and not app_name:
                continue
            display = title or app_name
            results.append(WindowInfo(id=wid, title=display, app_name=app_name))
        return results

    def get_window_rect(self, window_id: int | str) -> tuple[int, int, int, int] | None:
        import Quartz

        wid = int(window_id)
        win_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionIncludingWindow, wid
        )
        if not win_list:
            return None
        bounds = win_list[0].get("kCGWindowBounds")
        if not bounds:
            return None
        x = int(bounds["X"])
        y = int(bounds["Y"])
        w = int(bounds["Width"])
        h = int(bounds["Height"])
        return x, y, w, h
