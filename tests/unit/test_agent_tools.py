import asyncio
import re
import time
from datetime import datetime

from reef.agent import tools as agent_tools
from reef.agent.tools import get_current_time, set_timer


def test_get_current_time_returns_iso_like_string():
    out = get_current_time()
    assert re.search(r"\d{1,2}:\d{2}", out)


def test_get_current_time_matches_now_hour():
    out = get_current_time()
    assert datetime.now().strftime("%H:%M") in out


def test_set_timer_confirms_minutes():
    out = set_timer(10)
    assert "10" in out
    assert re.search(r"\d{1,2}:\d{2}", out)  # mentions a target clock time


def test_set_timer_actually_fires_notify_when_no_loop(monkeypatch):
    """Caller has no asyncio loop (the sync path) — the timer must still fire.
    Uses minutes=0 → 1s minimum delay so the test stays fast."""
    fired = []
    monkeypatch.setattr(agent_tools, "notify", lambda title, msg: fired.append((title, msg)))

    set_timer(0)
    # threading.Timer is daemon; allow up to ~2s for it to elapse on slow CI.
    for _ in range(40):
        if fired:
            break
        time.sleep(0.05)

    assert fired, "set_timer must invoke notify() once the delay elapses"
    title, msg = fired[0]
    assert "timer" in title.lower()
    assert "done" in msg.lower()


def test_set_timer_actually_fires_notify_when_loop_is_running(monkeypatch):
    """Caller is inside the asyncio loop (Gemini tool-call path) — set_timer
    must use loop.call_later, and the same notify callback must fire."""
    fired = []
    monkeypatch.setattr(agent_tools, "notify", lambda title, msg: fired.append((title, msg)))

    async def _run():
        set_timer(0)
        # Yield to the loop long enough for the call_later to elapse.
        await asyncio.sleep(1.3)

    asyncio.run(_run())
    assert fired, "set_timer must invoke notify() inside the asyncio loop too"
