import re
from datetime import datetime
from reef.agent.tools import get_current_time

def test_get_current_time_returns_iso_like_string():
    out = get_current_time()
    assert re.search(r"\d{1,2}:\d{2}", out)

def test_get_current_time_matches_now_hour():
    out = get_current_time()
    assert datetime.now().strftime("%H:%M") in out
