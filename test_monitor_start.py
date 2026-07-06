import os
import tempfile

os.environ["MONITOR_DATA_DIR"] = tempfile.mkdtemp(prefix="emby-monitor-idempotent-")

from backend.app import series_monitor


def test_start_monitor_is_idempotent(monkeypatch):
    calls = []

    class FakeScheduler:
        def __init__(self):
            self.running = False
        def add_job(self, *args, **kwargs):
            calls.append(("add_job", kwargs.get("id")))
        def start(self):
            calls.append(("start", None))
            self.running = True
        def reschedule_job(self, job_id, trigger):
            calls.append(("reschedule", job_id))

    fake = FakeScheduler()
    monkeypatch.setattr(series_monitor, "scheduler", fake)
    monkeypatch.setattr(series_monitor, "_build_trigger", lambda: "trigger")

    series_monitor.start_monitor()
    series_monitor.start_monitor()

    assert calls == [
        ("add_job", "series_monitor"),
        ("start", None),
        ("reschedule", "series_monitor"),
    ]


def test_start_monitor_recreates_scheduler_when_event_loop_is_closed(monkeypatch):
    calls = []

    class ClosedLoopScheduler:
        running = True
        def reschedule_job(self, job_id, trigger):
            calls.append(("reschedule_failed", job_id))
            raise RuntimeError("Event loop is closed")
        def shutdown(self, wait=False):
            calls.append(("shutdown", wait))

    class FreshScheduler:
        running = False
        def __init__(self, timezone=None):
            calls.append(("new", str(timezone)))
        def add_job(self, *args, **kwargs):
            calls.append(("add_job", kwargs.get("id")))
        def start(self):
            calls.append(("start", None))

    monkeypatch.setattr(series_monitor, "scheduler", ClosedLoopScheduler())
    monkeypatch.setattr(series_monitor, "AsyncIOScheduler", FreshScheduler)
    monkeypatch.setattr(series_monitor, "_build_trigger", lambda: "trigger")

    series_monitor.start_monitor()

    assert calls == [
        ("reschedule_failed", "series_monitor"),
        ("shutdown", False),
        ("new", str(series_monitor.MONITOR_TIMEZONE)),
        ("add_job", "series_monitor"),
        ("start", None),
    ]
