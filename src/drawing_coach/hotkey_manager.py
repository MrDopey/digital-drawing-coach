from __future__ import annotations

import sys
from typing import Callable

from pynput import keyboard


def _patch_macos_keycode_context() -> None:
    """Work around a pynput/macOS crash (upstream issue #511, still open).

    pynput's Darwin keyboard Listener recomputes its keycode context by
    calling Carbon's TIS APIs from its own background thread every time it
    starts. Newer macOS versions require those calls to happen on the main
    thread and hard-crash the process (SIGTRAP) otherwise — with no Python
    exception to catch, since the crash happens on pynput's listener thread
    after start() has already returned. pynput's Controller never hits this
    because it computes the same context in its __init__, i.e. on the
    caller's thread. We do the same for Listener: compute the context once,
    here on the main thread, and patch Listener to reuse it instead of
    recomputing it in the background.
    """
    from pynput._util.darwin import keycode_context
    from pynput.keyboard._darwin import Listener as _DarwinListener

    if getattr(_DarwinListener, "_main_thread_keycode_context", None) is not None:
        return

    with keycode_context() as context:
        cached_context = context
    _DarwinListener._main_thread_keycode_context = cached_context

    def _run(self) -> None:
        self._context = _DarwinListener._main_thread_keycode_context
        try:
            super(_DarwinListener, self)._run()
        finally:
            self._context = None

    _DarwinListener._run = _run


if sys.platform == "darwin":
    _patch_macos_keycode_context()


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
            self._listener = keyboard.GlobalHotKeys({self._hotkey_str: self._fired})
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
