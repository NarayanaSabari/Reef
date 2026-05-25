from datetime import datetime
from reef.shell.schedule import next_fire_time, seconds_until

def test_next_fire_is_today_when_upcoming():
    now = datetime(2026, 5, 25, 6, 0)
    assert next_fire_time(now, 8, 30) == datetime(2026, 5, 25, 8, 30)

def test_next_fire_is_tomorrow_when_passed():
    now = datetime(2026, 5, 25, 9, 0)
    assert next_fire_time(now, 8, 30) == datetime(2026, 5, 26, 8, 30)

def test_seconds_until_positive():
    now = datetime(2026, 5, 25, 6, 0)
    assert seconds_until(now, 8, 30) == 2.5 * 3600
