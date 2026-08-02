from __future__ import annotations

from typing import TYPE_CHECKING

from drawing_coach.window_manager import WindowInfo

if TYPE_CHECKING:
    from PIL import Image


def has_screen_recording_permission() -> bool:
    import Quartz  # type: ignore[import-not-found]

    win_list = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID
    )
    return bool(win_list)


def has_accessibility_permission() -> bool:
    import ctypes
    import ctypes.util

    path = ctypes.util.find_library("ApplicationServices")
    if not path:
        return False
    lib = ctypes.CDLL(path)
    lib.AXIsProcessTrustedWithOptions.restype = ctypes.c_bool
    lib.AXIsProcessTrustedWithOptions.argtypes = [ctypes.c_void_p]
    return bool(lib.AXIsProcessTrustedWithOptions(None))


def has_input_monitoring_permission() -> bool:
    import ctypes
    import ctypes.util

    try:
        path = ctypes.util.find_library("IOKit")
        if not path:
            return False
        lib = ctypes.CDLL(path)
        lib.IOHIDCheckAccess.restype = ctypes.c_uint32
        lib.IOHIDCheckAccess.argtypes = [ctypes.c_uint32]
        kIOHIDRequestTypeListenEvent = 1
        kIOHIDAccessTypeGranted = 0
        result = lib.IOHIDCheckAccess(kIOHIDRequestTypeListenEvent)
        return int(result) == kIOHIDAccessTypeGranted
    except Exception:
        return False


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

    def capture_image(self, window_id: int | str) -> Image.Image | None:
        """Capture just this window's own content via CoreGraphics.

        Uses CGRectNull + kCGWindowListOptionIncludingWindow so the render is
        scoped to the window itself, unlike a screen-rect grab (e.g. mss on
        macOS), which composites whatever is on-screen in that rectangle —
        including any overlapping windows.
        """
        import Quartz  # type: ignore[import-not-found]
        from PIL import Image

        wid = int(window_id)
        image_options = (
            Quartz.kCGWindowImageBoundsIgnoreFraming
            | Quartz.kCGWindowImageShouldBeOpaque
            | Quartz.kCGWindowImageNominalResolution
        )
        image_ref = Quartz.CGWindowListCreateImage(
            Quartz.CGRectNull,
            Quartz.kCGWindowListOptionIncludingWindow,
            wid,
            image_options,
        )
        if image_ref is None:
            return None

        width = Quartz.CGImageGetWidth(image_ref)
        height = Quartz.CGImageGetHeight(image_ref)
        if width <= 0 or height <= 0:
            return None

        provider = Quartz.CGImageGetDataProvider(image_ref)
        data = bytes(Quartz.CGDataProviderCopyData(provider))

        bytes_per_row = Quartz.CGImageGetBytesPerRow(image_ref)
        bytes_per_pixel = (Quartz.CGImageGetBitsPerPixel(image_ref) + 7) // 8
        if bytes_per_pixel * width != bytes_per_row:
            cropped = bytearray()
            for row in range(height):
                start = row * bytes_per_row
                end = start + width * bytes_per_pixel
                cropped.extend(data[start:end])
            data = bytes(cropped)

        return Image.frombytes("RGB", (width, height), data, "raw", "BGRX")
