from reef.memory.store import Memory
from reef.shell.brief import build_brief_prompt


def test_brief_is_terse_when_mornings_brief():
    p = build_brief_prompt([Memory("preference", "mornings", "brief")])
    assert "brief" in p.lower()

def test_brief_not_terse_without_pref():
    p = build_brief_prompt([])
    assert "paragraph" in p.lower()
