from datetime import datetime

from reef.shell.daily_scheduler import run_daily


async def test_run_daily_sleeps_until_time_then_fires():
    slept, fired = [], []
    async def fake_sleep(s): slept.append(s)
    async def cb(): fired.append(True)
    await run_daily(8, 30, cb, iterations=1, sleeper=fake_sleep,
                    now_fn=lambda: datetime(2026, 5, 25, 6, 0))
    assert slept == [2.5 * 3600]
    assert fired == [True]
