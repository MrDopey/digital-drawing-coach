from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING

from drawing_coach.window_manager import WindowInfo

if TYPE_CHECKING:
    from PIL import Image


class LinuxBackend:
    def list_windows(self) -> list[WindowInfo]:
        try:
            out = subprocess.check_output(
                ["xdotool", "search", "--onlyvisible", "--name", ""],
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return []

        results: list[WindowInfo] = []
        for wid_str in out.strip().splitlines():
            wid = int(wid_str)
            title = self._get_title(wid)
            if not title:
                continue
            results.append(WindowInfo(id=wid, title=title, app_name=""))
        return results

    def get_window_rect(self, window_id: int | str) -> tuple[int, int, int, int] | None:
        wid = int(window_id)
        try:
            out = subprocess.check_output(
                ["xdotool", "getwindowgeometry", "--shell", str(wid)],
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None

        props: dict[str, int] = {}
        for line in out.splitlines():
            m = re.match(r"(\w+)=(\d+)", line)
            if m:
                props[m.group(1)] = int(m.group(2))
        if {"X", "Y", "WIDTH", "HEIGHT"} <= props.keys():
            return props["X"], props["Y"], props["WIDTH"], props["HEIGHT"]
        return None

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

    def _get_title(self, wid: int) -> str:
        try:
            out = subprocess.check_output(
                ["xdotool", "getwindowname", str(wid)],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            return out.strip()
        except subprocess.CalledProcessError:
            return ""
