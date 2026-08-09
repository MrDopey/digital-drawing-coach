"""Tests for the opt-in perf instrumentation (drawing_coach.perf).

These verify the *mechanism*, not any macOS finding. Nothing here is evidence
about the sluggishness root cause — the artifact for that is a log from the
user's Mac.
"""

from __future__ import annotations

import gc
import logging
import threading

import pytest

from drawing_coach import perf


@pytest.fixture(autouse=True)
def _reset_perf():
    perf.reset_for_tests()
    yield
    perf.reset_for_tests()


@pytest.fixture
def records() -> list[logging.LogRecord]:
    """A logger whose records we can assert on, isolated from app logging."""
    log = logging.getLogger("drawing_coach.perf")
    captured: list[logging.LogRecord] = []

    class _Collector(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    handler = _Collector()
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    prev_propagate = log.propagate
    log.propagate = False
    try:
        yield captured
    finally:
        log.removeHandler(handler)
        log.propagate = prev_propagate


def _messages(records: list[logging.LogRecord]) -> list[str]:
    return [r.getMessage() for r in records]


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def _poll(
    wd: perf.StallWatchdog, clock: FakeClock, seconds: float, step: float
) -> None:
    """Drive the watchdog the way its real thread does: small, regular steps."""
    elapsed = 0.0
    while elapsed < seconds:
        clock.advance(step)
        wd.check_once()
        elapsed += step


# ---------------------------------------------------------------------------
# init() — env parsing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", ["", "0", "off", "false", "OFF"])
def test_init_disabled_values(value):
    assert perf.init(value) is False
    assert perf.ON is False
    assert perf.FULL is False


@pytest.mark.parametrize("value", ["1", "on", "true", "TRUE"])
def test_init_enabled_values(value):
    assert perf.init(value) is True
    assert perf.ON is True
    assert perf.FULL is False


def test_init_full_mode_enables_both_flags():
    assert perf.init("full") is True
    assert perf.ON is True
    assert perf.FULL is True


def test_init_unknown_value_disables_and_warns(capsys):
    assert perf.init("yes-please") is False
    assert perf.ON is False
    assert "yes-please" in capsys.readouterr().err


def test_init_parses_stall_threshold():
    perf.init("1", "500")
    assert perf.stall_threshold_ms() == pytest.approx(500.0)


@pytest.mark.parametrize("value", ["abc", "0", "-5"])
def test_init_invalid_stall_threshold_defaults_and_warns(value, capsys):
    perf.init("1", value)
    assert perf.stall_threshold_ms() == pytest.approx(perf.DEFAULT_STALL_MS)
    assert "DRAWING_COACH_PERF_STALL_MS" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# Probes — disabled path
# ---------------------------------------------------------------------------

def test_probes_are_no_ops_when_disabled(records):
    perf.init("0")
    with perf.probe("history.render", frames=50) as p:
        p.set(rows=50)
    perf.flush_aggregates()
    assert _messages(records) == []


def test_disabled_probe_allocates_no_timing_object():
    perf.init("0")
    with perf.probe("x") as p:
        assert p is perf._NULL


def test_decorator_is_transparent_when_disabled(records):
    perf.init("0")

    @perf.timed("thing")
    def add(a, b):
        return a + b

    assert add(2, 3) == 5
    assert _messages(records) == []


# ---------------------------------------------------------------------------
# Probes — enabled path
# ---------------------------------------------------------------------------

def test_probe_emits_label_thread_and_fields(records):
    perf.init("1")
    with perf.probe("history.render", frames=50) as p:
        p.set(rows=50)

    (msg,) = _messages(records)
    assert "PERF label=history.render" in msg
    assert "frames=50" in msg
    assert "rows=50" in msg
    assert f"thread={threading.current_thread().name}" in msg
    assert "ms=" in msg


def test_child_probes_fold_into_the_enclosing_probe(records):
    perf.init("1")
    with perf.probe("history.render"):
        for _ in range(3):
            with perf.probe("history.pil_to_pixmap", child=True):
                pass

    (msg,) = _messages(records)  # exactly one line: children do not emit
    assert "c.history.pil_to_pixmap.n=3" in msg
    assert "c.history.pil_to_pixmap.ms=" in msg
    assert "c.history.pil_to_pixmap.max_ms=" in msg


def test_nested_parent_probes_each_emit(records):
    perf.init("1")
    with perf.probe("outer"):
        with perf.probe("inner"):
            pass
    labels = [m.split()[1] for m in _messages(records)]
    assert labels == ["label=inner", "label=outer"]


def test_slow_probe_escalates_to_warning(records, monkeypatch):
    perf.init("1")
    monkeypatch.setattr(perf, "SLOW_MS", 0.0)
    with perf.probe("slow"):
        pass
    assert records[0].levelno == logging.WARNING


def test_fast_probe_stays_at_debug(records, monkeypatch):
    perf.init("1")
    monkeypatch.setattr(perf, "SLOW_MS", 10_000.0)
    with perf.probe("fast"):
        pass
    assert records[0].levelno == logging.DEBUG


def test_decorator_times_the_call(records):
    perf.init("1")

    @perf.timed("decorated")
    def work():
        return 42

    assert work() == 42
    assert work.__name__ == "work"
    assert "PERF label=decorated" in _messages(records)[0]


# ---------------------------------------------------------------------------
# Thread isolation — which thread pays is the open question
# ---------------------------------------------------------------------------

def test_child_probe_does_not_fold_into_another_threads_scope(records):
    perf.init("1")
    gate = threading.Event()
    released = threading.Event()

    def worker():
        gate.wait(timeout=2)
        # No enclosing scope on THIS thread, so this must aggregate, never
        # fold into the parent scope open on the main thread.
        with perf.probe("capture.write_png", child=True):
            pass
        released.set()

    t = threading.Thread(target=worker, name="capture-thread")
    t.start()
    with perf.probe("history.render"):
        gate.set()
        released.wait(timeout=2)
    t.join(timeout=2)

    (msg,) = _messages(records)
    assert "c.capture.write_png" not in msg

    perf.flush_aggregates()
    agg = [m for m in _messages(records) if m.startswith("PERF-AGG")]
    assert any("label=capture.write_png" in m and "thread=capture-thread" in m
               for m in agg)


def test_probe_line_names_the_executing_thread(records):
    perf.init("1")

    def worker():
        with perf.probe("capture.do_capture"):
            pass

    t = threading.Thread(target=worker, name="capture-thread")
    t.start()
    t.join(timeout=2)
    assert "thread=capture-thread" in _messages(records)[0]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def test_parentless_child_probes_aggregate_instead_of_spamming(records):
    perf.init("1")
    for _ in range(200):
        with perf.probe("history.row_paint", child=True):
            pass
    assert _messages(records) == []  # nothing emitted per call

    perf.flush_aggregates()
    (msg,) = _messages(records)
    assert msg.startswith("PERF-AGG")
    assert "label=history.row_paint" in msg
    assert "n=200" in msg
    assert "max_ms=" in msg


def test_flush_with_nothing_accumulated_emits_nothing(records):
    perf.init("1")
    perf.flush_aggregates()
    assert _messages(records) == []


def test_flush_clears_the_bucket(records):
    perf.init("1")
    with perf.probe("agg.me", child=True):
        pass
    perf.flush_aggregates()
    records.clear()
    perf.flush_aggregates()
    assert _messages(records) == []


# ---------------------------------------------------------------------------
# Instance tracking
# ---------------------------------------------------------------------------

class _Dummy:
    pass


def test_track_counts_live_instances():
    perf.init("1")
    a, b = _Dummy(), _Dummy()
    perf.track(a)
    perf.track(b)
    assert perf.instance_count("_Dummy") == 2


def test_tracking_does_not_retain_the_object():
    perf.init("1")
    obj = _Dummy()
    perf.track(obj)
    assert perf.instance_count("_Dummy") == 1
    del obj
    gc.collect()
    assert perf.instance_count("_Dummy") == 0


def test_track_ignores_non_weakrefable_objects():
    perf.init("1")
    perf.track(object())  # object() has no __weakref__
    assert perf.instance_counts() == {}


def test_instance_counts_omits_empty_classes():
    perf.init("1")
    obj = _Dummy()
    perf.track(obj)
    del obj
    gc.collect()
    assert "_Dummy" not in perf.instance_counts()


def test_signal_receivers_returns_minus_one_when_unavailable():
    assert perf.signal_receivers(object(), None) == -1


# ---------------------------------------------------------------------------
# GC probe
# ---------------------------------------------------------------------------

def test_gc_probe_installs_and_uninstalls_cleanly():
    perf.init("1")
    perf.install_gc_probe()
    assert perf._on_gc in gc.callbacks
    perf.install_gc_probe()  # idempotent
    assert gc.callbacks.count(perf._on_gc) == 1
    perf.uninstall_gc_probe()
    assert perf._on_gc not in gc.callbacks


def test_reset_removes_the_gc_callback():
    perf.init("1")
    perf.install_gc_probe()
    perf.reset_for_tests()
    assert perf._on_gc not in gc.callbacks


def test_long_gc_pause_is_reported(records, monkeypatch):
    perf.init("1")
    monkeypatch.setattr(perf, "GC_REPORT_MS", 0.0)
    perf._on_gc("start", {"generation": 2})
    perf._on_gc("stop", {"generation": 2, "collected": 118, "uncollectable": 0})
    (msg,) = _messages(records)
    assert msg.startswith("PERF-GC gen=2")
    assert "collected=118" in msg


def test_short_gc_pause_is_not_reported(records, monkeypatch):
    perf.init("1")
    monkeypatch.setattr(perf, "GC_REPORT_MS", 10_000.0)
    perf._on_gc("start", {"generation": 0})
    perf._on_gc("stop", {"generation": 0, "collected": 1, "uncollectable": 0})
    assert _messages(records) == []


# ---------------------------------------------------------------------------
# Stall watchdog
# ---------------------------------------------------------------------------

def _watchdog(clock: FakeClock) -> perf.StallWatchdog:
    wd = perf.StallWatchdog(threshold_s=0.25, poll_s=0.05, clock=clock)
    wd.beat()
    return wd


def test_responsive_event_loop_reports_no_stall(records):
    perf.init("1")
    clock = FakeClock()
    wd = _watchdog(clock)
    for _ in range(20):
        clock.advance(0.05)
        wd.beat()
        wd.check_once()
    assert [m for m in _messages(records) if "STALL" in m] == []
    assert wd.stalls == []


def test_blocked_event_loop_reports_begin_and_end(records):
    perf.init("1")
    clock = FakeClock()
    wd = _watchdog(clock)

    _poll(wd, clock, seconds=1.8, step=0.05)  # loop blocked: no beat()
    clock.advance(0.05)
    wd.beat()
    wd.check_once()

    msgs = _messages(records)
    assert sum(m.startswith("PERF-STALL-BEGIN") for m in msgs) == 1
    assert sum(m.startswith("PERF-STALL-END") for m in msgs) == 1


def test_stall_duration_is_measured_heartbeat_to_heartbeat(records):
    perf.init("1")
    clock = FakeClock()
    wd = _watchdog(clock)

    _poll(wd, clock, seconds=1.8, step=0.05)
    clock.advance(0.05)
    wd.beat()
    wd.check_once()

    (record,) = wd.stalls
    # ~1.85s blocked, not the 250ms detection latency.
    assert record.duration_ms == pytest.approx(1850.0, abs=60.0)


def test_one_stall_produces_exactly_one_begin_and_one_end(records):
    perf.init("1")
    clock = FakeClock()
    wd = _watchdog(clock)

    _poll(wd, clock, seconds=10.0, step=0.05)  # a very long stall
    clock.advance(0.05)
    wd.beat()
    wd.check_once()

    msgs = _messages(records)
    assert sum(m.startswith("PERF-STALL-BEGIN") for m in msgs) == 1
    assert sum(m.startswith("PERF-STALL-END") for m in msgs) == 1


def test_long_stall_is_resampled_up_to_the_cap(records):
    perf.init("1")
    clock = FakeClock()
    wd = _watchdog(clock)

    _poll(wd, clock, seconds=60.0, step=0.05)
    samples = [m for m in _messages(records) if m.startswith("PERF-STALL-SAMPLE")]
    assert 1 <= len(samples) <= perf.MAX_SAMPLES_PER_STALL - 1


def test_repeated_stall_signature_collapses_to_a_counted_line(records):
    perf.init("1")
    clock = FakeClock()
    wd = _watchdog(clock)

    for _ in range(3):
        _poll(wd, clock, seconds=0.6, step=0.05)
        clock.advance(0.05)
        wd.beat()
        wd.check_once()

    msgs = _messages(records)
    begins = [m for m in msgs if m.startswith("PERF-STALL-BEGIN")]
    repeats = [m for m in msgs if m.startswith("PERF-STALL-REPEAT")]
    # Same call site every time -> one full stack, the rest collapsed.
    assert len(begins) == 1
    assert len(repeats) == 2
    assert "count=3" in repeats[-1]


def test_stall_record_is_a_single_atomic_log_record(records):
    perf.init("1")
    clock = FakeClock()
    wd = _watchdog(clock)
    _poll(wd, clock, seconds=0.6, step=0.05)

    begin = next(r for r in records if r.getMessage().startswith("PERF-STALL-BEGIN"))
    # The stack lives inside one record, so concurrent logging cannot interleave.
    assert "\n  | " in begin.getMessage()


def test_stall_stack_names_the_gui_thread_frame(records):
    perf.init("1")
    clock = FakeClock()
    wd = _watchdog(clock)
    _poll(wd, clock, seconds=0.6, step=0.05)

    begin = next(m for m in _messages(records) if m.startswith("PERF-STALL-BEGIN"))
    assert "(gui)" in begin
    assert "test_perf.py" in begin


def test_watchdog_starved_by_a_gil_holding_call_is_tagged_late(records):
    perf.init("1")
    clock = FakeClock()
    wd = _watchdog(clock)

    # One giant jump: the watchdog thread never got scheduled during the stall.
    clock.advance(3.0)
    wd.check_once()

    begin = next(m for m in _messages(records) if m.startswith("PERF-STALL-BEGIN"))
    assert "sampled_late=1" in begin


def test_normal_polling_is_not_tagged_late(records):
    perf.init("1")
    clock = FakeClock()
    wd = _watchdog(clock)
    _poll(wd, clock, seconds=0.6, step=0.05)

    begin = next(m for m in _messages(records) if m.startswith("PERF-STALL-BEGIN"))
    assert "sampled_late=0" in begin


def test_gui_thread_is_identified_from_the_heartbeat():
    perf.init("1")
    clock = FakeClock()
    wd = perf.StallWatchdog(clock=clock)
    assert wd.gui_ident is None

    result: list[int | None] = []

    def beat_from_worker():
        wd.beat()
        result.append(wd.gui_ident)

    t = threading.Thread(target=beat_from_worker, name="pretend-gui")
    t.start()
    t.join(timeout=2)
    # Identified by whoever runs the heartbeat, not assumed to be MainThread.
    assert result == [t.ident]
    assert wd.gui_ident != threading.main_thread().ident


def test_stall_record_carries_signature_and_top_frame(records):
    perf.init("1")
    clock = FakeClock()
    wd = _watchdog(clock)
    _poll(wd, clock, seconds=0.6, step=0.05)
    clock.advance(0.05)
    wd.beat()
    wd.check_once()

    (record,) = wd.stalls
    assert len(record.signature) == 8
    assert "test_perf.py" in record.top_frame


# ---------------------------------------------------------------------------
# Summary / snapshot
# ---------------------------------------------------------------------------

def test_log_summary_is_silent_when_disabled(records):
    perf.init("0")
    perf.log_summary()
    assert _messages(records) == []


def test_log_summary_reports_labels_and_stalls(records):
    perf.init("1")
    with perf.probe("history.render"):
        pass
    records.clear()
    perf.log_summary()
    (msg,) = _messages(records)
    assert msg.startswith("PERF-SUMMARY")
    assert "history.render:1/" in msg


def test_snapshot_includes_counts_and_log_destination():
    perf.init("1")
    perf.set_log_destination("/tmp/perf.log")
    obj = _Dummy()
    perf.track(obj)
    with perf.probe("history.render"):
        pass

    text = perf.snapshot()
    assert "instrumentation: on" in text
    assert "/tmp/perf.log" in text
    assert "_Dummy=1" in text
    assert "history.render" in text


def test_install_watchdog_is_a_no_op_when_disabled():
    perf.init("0")
    assert perf.install_watchdog() is None
    assert perf._watchdog is None
    assert perf._on_gc not in gc.callbacks
