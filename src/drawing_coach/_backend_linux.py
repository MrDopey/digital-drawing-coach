from __future__ import annotations

import re
import subprocess

from drawing_coach.window_manager import WindowInfo


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
