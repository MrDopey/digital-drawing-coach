from __future__ import annotations

from typing import Callable

from pynput import keyboard


class HotkeyManager:
    """Registers and unregisters a global hotkey using pynput."""

    DEFAULT_HOTKEY = "<ctrl>+<shift>+f"

    def __init__(self) -> None:
        self._hotkey_str: str = self.DEFAULT_HOTKEY
        self._listener: keyboard.GlobalHotKeys | None = None
        self.on_trigger: Callable[[], None] | None = None

    @property
    def hotkey(self) -> str:
        return self._hotkey_str

    def set_hotkey(self, hotkey_str: str) -> None:
        """Change the registered hotkey; takes effect immediately."""
        self._stop()
        self._hotkey_str = hotkey_str
        self._start()

    def start(self) -> None:
        self._start()

    def stop(self) -> None:
        self._stop()

    # ------------------------------------------------------------------

    def _start(self) -> None:
        if not self._hotkey_str:
            return
        try:
            self._listener = keyboard.GlobalHotKeys(
                {self._hotkey_str: self._fired}
            )
            self._listener.start()
        except Exception:
            self._listener = None

    def _stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _fired(self) -> None:
        if self.on_trigger:
            self.on_trigger()
