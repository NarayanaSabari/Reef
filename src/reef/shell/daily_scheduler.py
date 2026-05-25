import asyncio
from datetime import datetime
from reef.shell.schedule import seconds_until


async def run_daily(hour, minute, callback, *, iterations=None,
                    sleeper=asyncio.sleep, now_fn=datetime.now) -> None:
    """Sleep until hour:minute, fire callback, repeat. `iterations` bounds it for tests."""
    count = 0
    while iterations is None or count < iterations:
        await sleeper(seconds_until(now_fn(), hour, minute))
        await callback()
        count += 1
