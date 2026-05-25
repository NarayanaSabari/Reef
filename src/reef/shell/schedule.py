from datetime import datetime, timedelta


def next_fire_time(now: datetime, hour: int, minute: int) -> datetime:
    """Next occurrence of hour:minute at or after `now` (today if upcoming, else tomorrow)."""
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def seconds_until(now: datetime, hour: int, minute: int) -> float:
    return (next_fire_time(now, hour, minute) - now).total_seconds()
