from __future__ import annotations

from drawing_coach.window_manager import WindowInfo


def has_screen_recording_permission() -> bool:
    import Quartz  # type: ignore[import-not-found]

    win_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID
    )
    return bool(win_list)


def has_input_monitoring_permission() -> bool:
    import ctypes
    import ctypes.util

    path = ctypes.util.find_library("ApplicationServices")
    if not path:
        return False
    lib = ctypes.CDLL(path)
    lib.AXIsProcessTrustedWithOptions.restype = ctypes.c_bool
    lib.AXIsProcessTrustedWithOptions.argtypes = [ctypes.c_void_p]
    return bool(lib.AXIsProcessTrustedWithOptions(None))


class MacOSBackend:
    def list_windows(self) -> list[WindowInfo]:
        import Quartz  # type: ignore[import-not-found]

        options = (
            Quartz.kCGWindowListOptionOnScreenOnly
            | Quartz.kCGWindowListExcludeDesktopElements
        )
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
        import Quartz  # type: ignore[import-not-found]

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
