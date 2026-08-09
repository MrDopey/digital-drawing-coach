"""Opt-in GUI-thread stall watchdog and scoped timing probes.

Entirely inert unless ``DRAWING_COACH_PERF_WATCHDOG`` is set: :data:`ON` is a
module-level bool written once by :func:`init`, and every public entry point
short-circuits on it. When off, no timer, thread, GC callback or log handler is
created, and the hot call sites guard on ``perf.ON`` so nothing is even
allocated.

Why this exists: a macOS-only sluggishness report survived four fixes that were
each validated only on Linux/Xvfb. The missing input was never a hypothesis, it
was a measurement from the machine that reproduces the problem. This module is
that measurement channel.
"""

from __future__ import annotations

import gc
import hashlib
import logging
import sys
import threading
import time
import traceback
import weakref
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, TypeVar

_log = logging.getLogger("drawing_coach.perf")

F = TypeVar("F", bound=Callable[..., Any])

# --- Configuration ---------------------------------------------------------

ON: bool = False
FULL: bool = False
"""``DRAWING_COACH_PERF_WATCHDOG=full`` — also arms the faulthandler fallback."""

DEFAULT_STALL_MS = 250
SLOW_MS = 100.0
"""Probes at or above this escalate from DEBUG to WARNING, so the user does not
have to raise DRAWING_COACH_LOG_LEVEL to see the interesting records."""
HEARTBEAT_MS = 100
POLL_S = 0.05
AGG_WINDOW_S = 5.0
GC_REPORT_MS = 50.0
STACK_DEPTH = 8
OTHER_THREAD_DEPTH = 3
MAX_SAMPLES_PER_STALL = 5
SAMPLE_BACKOFF_S = (0.5, 1.5, 3.5, 7.5)
SIGNATURE_DEDUPE_S = 30.0

_stall_threshold_s: float = DEFAULT_STALL_MS / 1000.0

_TRUE = {"1", "on", "true"}
_FALSE = {"", "0", "off", "false"}


def init(raw_watchdog: str, raw_stall_ms: str = "") -> bool:
    """Parse the env values and arm the module. Returns whether it is enabled."""
    global ON, FULL, _stall_threshold_s

    value = (raw_watchdog or "").strip().lower()
    if value in _FALSE:
        ON = FULL = False
    elif value in _TRUE:
        ON, FULL = True, False
    elif value == "full":
        ON = FULL = True
    else:
        print(
            f'Unknown DRAWING_COACH_PERF_WATCHDOG "{raw_watchdog}",'
            " performance instrumentation disabled",
            file=sys.stderr,
        )
        ON = FULL = False

    stall_ms = DEFAULT_STALL_MS
    raw = (raw_stall_ms or "").strip()
    if raw:
        try:
            parsed = int(raw)
            if parsed <= 0:
                raise ValueError("must be positive")
            stall_ms = parsed
        except (ValueError, OverflowError):
            print(
                f'Invalid DRAWING_COACH_PERF_STALL_MS "{raw}",'
                f" defaulting to {DEFAULT_STALL_MS}",
                file=sys.stderr,
            )
    _stall_threshold_s = stall_ms / 1000.0
    return ON


def stall_threshold_ms() -> float:
    return _stall_threshold_s * 1000.0


# --- Scoped probes ---------------------------------------------------------


class _Local(threading.local):
    def __init__(self) -> None:
        self.stack: list[Probe] = []


_tls = _Local()

# Parentless high-frequency probes (paintEvent, hover hit-test) accumulate here
# rather than emitting a line each: repaint *frequency* is as diagnostic as
# duration, and per-event lines would be unreadable.
_agg_lock = threading.Lock()
_agg: dict[tuple[str, str], list[float]] = {}  # (label, thread) -> [n, total, max]
_agg_started = time.monotonic()

_totals_lock = threading.Lock()
_totals: dict[str, list[float]] = {}  # label -> [n, total_ms]


class Probe:
    """Times a block. Use via :func:`probe` or :func:`timed`, not directly."""

    __slots__ = ("label", "fields", "child", "_t0", "_children", "_active")

    def __init__(self, label: str, *, child: bool = False, **fields: object) -> None:
        self.label = label
        self.child = child
        self.fields: dict[str, object] = dict(fields)
        self._children: dict[str, list[float]] = {}
        self._t0 = 0.0
        self._active = False

    def set(self, **fields: object) -> None:
        """Record fields only knowable inside the block."""
        if self._active:
            self.fields.update(fields)

    def __enter__(self) -> Probe:
        self._active = True
        self._t0 = time.perf_counter()
        if not self.child:
            _tls.stack.append(self)
        return self

    def __exit__(self, *exc: object) -> None:
        ms = (time.perf_counter() - self._t0) * 1000.0
        self._active = False
        if not self.child:
            if _tls.stack and _tls.stack[-1] is self:
                _tls.stack.pop()
            self._emit(ms)
            return

        # Fold into the enclosing scope on this thread. Thread-local is
        # load-bearing: which thread pays is precisely the open question, so a
        # capture-thread probe must never fold into a GUI-thread scope.
        parent = _tls.stack[-1] if _tls.stack else None
        if parent is not None:
            slot = parent._children.setdefault(self.label, [0.0, 0.0, 0.0])
        else:
            with _agg_lock:
                slot = _agg.setdefault(
                    (self.label, threading.current_thread().name), [0.0, 0.0, 0.0]
                )
                slot[0] += 1
                slot[1] += ms
                slot[2] = max(slot[2], ms)
            return
        slot[0] += 1
        slot[1] += ms
        slot[2] = max(slot[2], ms)

    def _emit(self, ms: float) -> None:
        with _totals_lock:
            slot = _totals.setdefault(self.label, [0.0, 0.0])
            slot[0] += 1
            slot[1] += ms

        parts = [
            f"PERF label={self.label}",
            f"ms={ms:.1f}",
            f"thread={threading.current_thread().name}",
        ]
        parts += [f"{k}={v}" for k, v in self.fields.items()]
        for label, (n, total, peak) in sorted(self._children.items()):
            parts += [
                f"c.{label}.n={int(n)}",
                f"c.{label}.ms={total:.1f}",
                f"c.{label}.max_ms={peak:.1f}",
            ]
        _log.log(
            logging.WARNING if ms >= SLOW_MS else logging.DEBUG, " ".join(parts)
        )


class _NullProbe:
    """Returned when instrumentation is off — no timing, no allocation churn."""

    __slots__ = ()

    def set(self, **fields: object) -> None:
        return None

    def __enter__(self) -> _NullProbe:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


_NULL = _NullProbe()


def probe(label: str, *, child: bool = False, **fields: object) -> Any:
    """Time a block. ``child=True`` folds into the enclosing probe."""
    if not ON:
        return _NULL
    return Probe(label, child=child, **fields)


def timed(label: str, *, child: bool = False, **fields: object) -> Callable[[F], F]:
    """Decorator form of :func:`probe`."""

    def decorate(fn: F) -> F:
        def wrapper(*args: object, **kwargs: object) -> object:
            if not ON:
                return fn(*args, **kwargs)
            with Probe(label, child=child, **fields):
                return fn(*args, **kwargs)

        wrapper.__name__ = getattr(fn, "__name__", label)
        wrapper.__doc__ = fn.__doc__
        wrapper.__wrapped__ = fn  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorate


def flush_aggregates() -> None:
    """Emit one PERF-AGG line per (label, thread) accumulated since the last flush."""
    global _agg_started
    if not ON:
        return
    with _agg_lock:
        if not _agg:
            _agg_started = time.monotonic()
            return
        snapshot = dict(_agg)
        _agg.clear()
        window = time.monotonic() - _agg_started
        _agg_started = time.monotonic()

    for (label, thread), (n, total, peak) in sorted(snapshot.items()):
        _log.debug(
            "PERF-AGG window_s=%.1f label=%s n=%d ms=%.1f max_ms=%.1f thread=%s",
            window,
            label,
            int(n),
            total,
            peak,
            thread,
        )


# --- Application-wide input probe ------------------------------------------
#
# Counts every mouse event the process receives, independently of whether Qt
# routes it anywhere useful. The viewport-level `history.hover_hit_test` probe
# only sees moves that reach one widget; comparing the two separates "events
# never arrive" from "events arrive but are not routed to the dialog".

_input_lock = threading.Lock()
_input_counts: dict[str, int] = defaultdict(int)
_move_receivers: dict[str, int] = defaultdict(int)
_input_state: str = "unknown"
_input_probe: Any = None
_input_timer: Any = None


def _record_input(name: str, receiver: str | None) -> None:
    with _input_lock:
        _input_counts[name] += 1
        if receiver is not None:
            _move_receivers[receiver] += 1


def set_input_state(state: str) -> None:
    global _input_state
    _input_state = state


def install_input_probe() -> bool:
    """Install an application-wide mouse-event counter. No-op when disabled."""
    global _input_probe, _input_timer
    if not ON or _input_probe is not None:
        return False

    from PyQt6.QtCore import QEvent, QObject, QTimer
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        return False

    # An event filter on the application object receives events for every
    # object in the app, so it must stay a dict increment and nothing more.
    types = {
        QEvent.Type.MouseMove: "move",
        QEvent.Type.HoverMove: "hover_move",
        QEvent.Type.MouseButtonPress: "press",
        QEvent.Type.MouseButtonRelease: "release",
        QEvent.Type.Enter: "enter",
        QEvent.Type.Leave: "leave",
        QEvent.Type.Wheel: "wheel",
    }

    class _InputProbe(QObject):
        def eventFilter(self, obj, event):  # noqa: N802 - Qt override
            name = types.get(event.type())
            if name is not None:
                _record_input(
                    name,
                    type(obj).__name__ if name in ("move", "hover_move") else None,
                )
            return False

    probe_obj = _InputProbe()
    app.installEventFilter(probe_obj)

    def _sample_state() -> None:
        # Sampled on the GUI thread — the flush runs on the watchdog thread and
        # must never touch Qt objects.
        active = QApplication.activeWindow()
        focus = QApplication.focusWidget()
        set_input_state(
            f"app_state={int(QApplication.applicationState().value)}"
            f" active={type(active).__name__ if active else 'none'}"
            f" focus={type(focus).__name__ if focus else 'none'}"
        )

    timer = QTimer()
    timer.setInterval(1000)
    timer.timeout.connect(_sample_state)
    timer.start()

    _input_probe = probe_obj
    _input_timer = timer
    return True


def flush_input() -> None:
    """Emit one PERF-INPUT line per aggregation window."""
    if not ON:
        return
    with _input_lock:
        if not _input_counts:
            return
        counts = dict(_input_counts)
        receivers = dict(_move_receivers)
        _input_counts.clear()
        _move_receivers.clear()

    top = sorted(receivers.items(), key=lambda kv: -kv[1])[:4]
    _log.warning(
        "PERF-INPUT %s %s move_to=%s",
        " ".join(f"{k}={v}" for k, v in sorted(counts.items())),
        _input_state,
        ",".join(f"{k}:{v}" for k, v in top) or "none",
    )


# --- Live instance / receiver counts ---------------------------------------

_instances: dict[str, weakref.WeakSet[Any]] = defaultdict(weakref.WeakSet)


def track(obj: object) -> None:
    """Record a live instance without retaining it.

    Called unconditionally (a WeakSet.add is ~1us) from every modal dialog that
    is parented to MainWindow and never deleted, so the log states which panels
    actually accumulate on the user's machine.
    """
    try:
        _instances[type(obj).__name__].add(obj)
    except TypeError:  # not weak-referenceable
        pass


def instance_count(name: str) -> int:
    return len(_instances.get(name, ()))


def instance_counts() -> dict[str, int]:
    return {name: len(s) for name, s in _instances.items() if len(s)}


def signal_receivers(obj: Any, signal: Any) -> int:
    """Number of slots connected to ``signal`` on ``obj``; -1 if unavailable."""
    try:
        return int(obj.receivers(signal))
    except Exception:
        return -1


def log_open(dialog: str, engine: Any = None) -> None:
    """Emit PERF-OPEN after a modal dialog's exec() returns."""
    if not ON:
        return
    receivers = (
        signal_receivers(engine, engine.frames_changed) if engine is not None else -1
    )
    _log.warning(
        "PERF-OPEN dialog=%s live_after=%d frames_changed_receivers=%d",
        dialog,
        instance_count(dialog),
        receivers,
    )


# --- GC pause probe --------------------------------------------------------

_gc_t0: float = 0.0
_gc_runs: dict[int, int] = defaultdict(int)


def _on_gc(phase: str, info: dict[str, int]) -> None:
    global _gc_t0
    if phase == "start":
        _gc_t0 = time.perf_counter()
        return
    ms = (time.perf_counter() - _gc_t0) * 1000.0
    gen = int(info.get("generation", -1))
    _gc_runs[gen] += 1
    if ms >= GC_REPORT_MS:
        _log.warning(
            "PERF-GC gen=%d ms=%.1f collected=%d uncollectable=%d thread=%s",
            gen,
            ms,
            info.get("collected", -1),
            info.get("uncollectable", -1),
            threading.current_thread().name,
        )


def install_gc_probe() -> None:
    if _on_gc not in gc.callbacks:
        gc.callbacks.append(_on_gc)


def uninstall_gc_probe() -> None:
    while _on_gc in gc.callbacks:
        gc.callbacks.remove(_on_gc)


# --- Stall watchdog --------------------------------------------------------


@dataclass
class StallRecord:
    started_at: float
    duration_ms: float
    samples: int
    signature: str
    top_frame: str
    sampled_late: bool = False
    stacks: list[str] = field(default_factory=list)


class StallWatchdog:
    """Detects a blocked Qt event loop and reports what was on its stack.

    The GUI thread is identified by whichever thread runs :meth:`beat` — the
    timer callback runs on the thread owning the timer, which is the thread
    running the event loop. This does not assume GUI thread == main thread.
    """

    def __init__(
        self,
        *,
        threshold_s: float | None = None,
        poll_s: float = POLL_S,
        clock: Callable[[], float] = time.monotonic,
        log: logging.Logger | None = None,
    ) -> None:
        self._threshold_s = (
            _stall_threshold_s if threshold_s is None else threshold_s
        )
        self._poll_s = poll_s
        self._clock = clock
        self._log = log or _log

        self._last_beat = clock()
        self._gui_ident: int | None = None
        self._started_at = clock()

        self._in_stall = False
        self._beat_before_stall = 0.0
        self._stall_started_at = 0.0
        self._samples = 0
        self._next_sample_at = 0.0
        self._current_sig = ""
        self._current_top = ""

        self._last_loop_at = clock()
        self._sampled_late = False

        self._stalls: list[StallRecord] = []
        self._sig_counts: dict[str, int] = defaultdict(int)
        self._sig_last_full: dict[str, float] = {}

        self._thread: threading.Thread | None = None
        self._running = False
        self._last_agg_flush = clock()

    # -- heartbeat ----------------------------------------------------------

    def beat(self) -> None:
        self._gui_ident = threading.get_ident()
        self._last_beat = self._clock()

    # -- introspection ------------------------------------------------------

    @property
    def stalls(self) -> list[StallRecord]:
        return list(self._stalls)

    @property
    def gui_ident(self) -> int | None:
        return self._gui_ident

    def uptime_s(self) -> float:
        return self._clock() - self._started_at

    # -- core loop ----------------------------------------------------------

    def check_once(self) -> None:
        """One watchdog iteration. Synchronous and clock-injectable, so stall
        detection is testable deterministically with no sleeps."""
        now = self._clock()

        # If our own iteration was delayed far beyond the poll interval, the
        # GIL was held by a native call: the duration is trustworthy but the
        # stack we are about to sample is not.
        loop_gap = now - self._last_loop_at
        self._sampled_late = loop_gap > max(self._poll_s * 4, self._threshold_s)
        self._last_loop_at = now

        age = now - self._last_beat

        if not self._in_stall:
            if age >= self._threshold_s:
                self._begin_stall(now, age)
            return

        if age < self._threshold_s:
            self._end_stall()
            return

        if now >= self._next_sample_at and self._samples < MAX_SAMPLES_PER_STALL:
            self._sample_stall(now, age)

    def _begin_stall(self, now: float, age: float) -> None:
        self._in_stall = True
        self._beat_before_stall = self._last_beat
        self._stall_started_at = now
        self._samples = 1

        stacks = self._capture_stacks()
        self._current_sig = _signature(stacks[0] if stacks else "")
        self._current_top = _top_frame(stacks[0] if stacks else "")
        self._sig_counts[self._current_sig] += 1
        self._schedule_next_sample(now)

        last_full = self._sig_last_full.get(self._current_sig)
        if last_full is not None and now - last_full < SIGNATURE_DEDUPE_S:
            self._log.warning(
                "PERF-STALL-REPEAT sig=%s count=%d ms=%.1f",
                self._current_sig,
                self._sig_counts[self._current_sig],
                age * 1000.0,
            )
            return

        self._sig_last_full[self._current_sig] = now
        self._log.warning(
            "PERF-STALL-BEGIN ms_so_far=%.1f threshold_ms=%.0f sig=%s"
            " sampled_late=%d panels=%s\n%s",
            age * 1000.0,
            self._threshold_s * 1000.0,
            self._current_sig,
            int(self._sampled_late),
            _counts_str(),
            _indent(stacks),
        )

    def _sample_stall(self, now: float, age: float) -> None:
        self._samples += 1
        stacks = self._capture_stacks()
        self._schedule_next_sample(now)
        self._log.warning(
            "PERF-STALL-SAMPLE seq=%d ms_so_far=%.1f sig=%s sampled_late=%d\n%s",
            self._samples - 1,
            age * 1000.0,
            self._current_sig,
            int(self._sampled_late),
            _indent(stacks),
        )

    def _end_stall(self) -> None:
        # Heartbeat-to-heartbeat: the true blocked interval, not the detection
        # latency (which would understate short stalls and depend on poll_s).
        duration_ms = (self._last_beat - self._beat_before_stall) * 1000.0
        self._in_stall = False
        record = StallRecord(
            started_at=self._stall_started_at,
            duration_ms=duration_ms,
            samples=self._samples,
            signature=self._current_sig,
            top_frame=self._current_top,
            sampled_late=self._sampled_late,
        )
        self._stalls.append(record)
        self._log.warning(
            "PERF-STALL-END ms=%.1f samples=%d sig=%s top=%s",
            duration_ms,
            self._samples,
            self._current_sig,
            self._current_top or "<none>",
        )

    def _schedule_next_sample(self, now: float) -> None:
        idx = min(self._samples - 1, len(SAMPLE_BACKOFF_S) - 1)
        self._next_sample_at = self._stall_started_at + SAMPLE_BACKOFF_S[idx]
        if self._next_sample_at <= now:
            self._next_sample_at = now + SAMPLE_BACKOFF_S[-1]

    def _capture_stacks(self) -> list[str]:
        """GUI-thread stack first, then the top frames of other live threads."""
        try:
            frames = sys._current_frames()  # type: ignore[attr-defined]
        except Exception:
            return []

        names = {t.ident: t.name for t in threading.enumerate()}
        out: list[str] = []

        gui_frame = frames.get(self._gui_ident) if self._gui_ident else None
        if gui_frame is not None:
            lines = _own_frames_removed(traceback.format_stack(gui_frame))
            out.append(
                f"-- {names.get(self._gui_ident, 'GUI')} (gui):\n"
                + "".join(lines[-STACK_DEPTH:])
            )
        else:
            out.append("-- gui thread frame unavailable")

        for ident, frame in frames.items():
            if ident == self._gui_ident:
                continue
            lines = _own_frames_removed(traceback.format_stack(frame))
            out.append(
                f"-- {names.get(ident, ident)}:\n"
                + "".join(lines[-OTHER_THREAD_DEPTH:])
            )
        return out

    # -- lifecycle ----------------------------------------------------------

    def _run(self) -> None:
        while self._running:
            try:
                self.check_once()
                if self._clock() - self._last_agg_flush >= AGG_WINDOW_S:
                    self._last_agg_flush = self._clock()
                    flush_aggregates()
                    flush_input()
                    _log_live()
            except Exception:  # never let the watchdog kill itself
                _log.debug("PERF watchdog iteration failed", exc_info=True)
            time.sleep(self._poll_s)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run, name="perf-watchdog", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False


_MODULE_FILE = __file__


def _own_frames_removed(lines: list[str]) -> list[str]:
    """Drop this module's own frames from a sampled stack.

    The watchdog normally samples the GUI thread from its own thread, so its
    frames are absent — but whenever the sampler and the sampled thread
    coincide, leaving them in would name perf.py as the culprit in its own
    stall report.
    """
    kept = [ln for ln in lines if _MODULE_FILE not in ln]
    return kept or lines


def _signature(stack: str) -> str:
    return hashlib.sha1(stack.encode("utf-8", "replace")).hexdigest()[:8]


def _top_frame(stack: str) -> str:
    for line in reversed(stack.splitlines()):
        line = line.strip()
        if line.startswith("File "):
            parts = line.split('"')
            if len(parts) >= 2:
                tail = parts[2] if len(parts) > 2 else ""
                return f"{parts[1].rsplit('/', 1)[-1]}{tail.rstrip(',')}"
    return ""


def _indent(stacks: list[str]) -> str:
    body = "\n".join(stacks)
    return "\n".join(f"  | {line}" for line in body.splitlines())


def _counts_str() -> str:
    counts = instance_counts()
    return ",".join(f"{k}={v}" for k, v in sorted(counts.items())) or "none"


def _log_live() -> None:
    counts = instance_counts()
    if counts:
        _log.debug("PERF-LIVE %s", _counts_str())


# --- Installation and reporting --------------------------------------------

_watchdog: StallWatchdog | None = None
_heartbeat: Any = None  # module-level ref so the QTimer is not collected


def install_watchdog() -> StallWatchdog | None:
    """Start the heartbeat timer and watchdog thread. No-op when disabled."""
    global _watchdog, _heartbeat
    if not ON or _watchdog is not None:
        return _watchdog

    from PyQt6.QtCore import Qt, QTimer

    wd = StallWatchdog()
    timer = QTimer()
    timer.setInterval(HEARTBEAT_MS)
    timer.setTimerType(Qt.TimerType.PreciseTimer)
    timer.timeout.connect(wd.beat)
    timer.start()

    _heartbeat = timer
    _watchdog = wd
    wd.beat()
    wd.start()
    install_gc_probe()
    install_input_probe()

    _log.warning(
        "PERF-WATCHDOG-START stall_ms=%.0f heartbeat_ms=%d poll_ms=%.0f"
        " gui_thread=%s:%s main_thread=%s pid=%s",
        stall_threshold_ms(),
        HEARTBEAT_MS,
        POLL_S * 1000.0,
        threading.current_thread().name,
        wd.gui_ident,
        threading.main_thread().ident,
        _pid(),
    )
    if FULL:
        _arm_faulthandler()
    return wd


def _pid() -> int:
    import os

    return os.getpid()


def _arm_faulthandler() -> None:
    """Fallback for stalls inside a native call that never releases the GIL —
    the Python sampler cannot run then, but faulthandler dumps from a C thread.

    Deliberately writes to its own file: routing raw dumps through the log
    handler would interleave unparseably with the formatted records.
    """
    import faulthandler

    from drawing_coach.paths import debug_log_dir

    try:
        dest = debug_log_dir() / "faulthandler.txt"
        dest.parent.mkdir(parents=True, exist_ok=True)
        handle = open(dest, "w")  # noqa: SIM115 - must outlive this function
        faulthandler.dump_traceback_later(5.0, repeat=True, file=handle, exit=False)
        _log.warning("PERF-FAULTHANDLER armed file=%s", dest)
    except OSError as exc:
        _log.warning("PERF-FAULTHANDLER could not arm: %s", exc)


def log_summary() -> None:
    """Emit PERF-SUMMARY. Wired to QApplication.aboutToQuit."""
    if not ON:
        return
    flush_aggregates()
    wd = _watchdog
    stalls = wd.stalls if wd else []
    total = sum(s.duration_ms for s in stalls)
    peak = max((s.duration_ms for s in stalls), default=0.0)
    top = sorted(
        (wd._sig_counts.items() if wd else []), key=lambda kv: -kv[1]
    )[:3]
    with _totals_lock:
        labels = ",".join(
            f"{k}:{int(v[0])}/{v[1]:.1f}ms" for k, v in sorted(_totals.items())
        )
    _log.warning(
        "PERF-SUMMARY uptime_s=%.1f stalls=%d stall_ms_total=%.1f stall_ms_max=%.1f"
        " top_sig=%s labels=%s",
        wd.uptime_s() if wd else 0.0,
        len(stalls),
        total,
        peak,
        ",".join(f"{s}:{n}" for s, n in top) or "none",
        labels or "none",
    )


def snapshot() -> str:
    """Human-readable summary for the Diagnostics "Copy Perf Snapshot" button."""
    gc.collect()
    wd = _watchdog
    stalls = wd.stalls if wd else []
    lines = [
        "Drawing Coach — perf snapshot",
        f"instrumentation: {'full' if FULL else 'on' if ON else 'off'}",
        f"stall threshold: {stall_threshold_ms():.0f} ms",
        f"uptime: {wd.uptime_s():.1f}s" if wd else "uptime: n/a",
        f"log file: {_log_destination()}",
        "",
        f"stalls: {len(stalls)}"
        f"  total={sum(s.duration_ms for s in stalls):.1f}ms"
        f"  max={max((s.duration_ms for s in stalls), default=0.0):.1f}ms",
    ]
    for sig, count in sorted(
        (wd._sig_counts.items() if wd else []), key=lambda kv: -kv[1]
    )[:3]:
        top = next((s.top_frame for s in stalls if s.signature == sig), "")
        lines.append(f"  {sig} x{count}  {top}")

    lines += ["", "live instances:"]
    counts = instance_counts()
    lines += [f"  {k}={v}" for k, v in sorted(counts.items())] or ["  none"]

    with _totals_lock:
        lines += ["", "probe totals:"]
        lines += [
            f"  {k}: n={int(v[0])} total={v[1]:.1f}ms"
            for k, v in sorted(_totals.items())
        ] or ["  none"]
    return "\n".join(lines)


_log_destination_value = "none"


def set_log_destination(dest: str) -> None:
    global _log_destination_value
    _log_destination_value = dest


def _log_destination() -> str:
    return _log_destination_value


def reset_for_tests() -> None:
    """Restore module state. Tests must call this so gc.callbacks stays clean."""
    global ON, FULL, _watchdog, _heartbeat, _stall_threshold_s
    global _input_probe, _input_timer
    if _watchdog is not None:
        _watchdog.stop()
    _watchdog = None
    _heartbeat = None
    if _input_timer is not None:
        _input_timer.stop()
    _input_probe = None
    _input_timer = None
    ON = FULL = False
    _stall_threshold_s = DEFAULT_STALL_MS / 1000.0
    uninstall_gc_probe()
    _tls.stack = []
    with _input_lock:
        _input_counts.clear()
        _move_receivers.clear()
    with _agg_lock:
        _agg.clear()
    with _totals_lock:
        _totals.clear()
    _instances.clear()


def _iter_stack() -> Iterator[Probe]:  # pragma: no cover - debugging aid
    yield from _tls.stack
