import pytest
from reef.agent.coral import ensure_coral_available

def test_raises_when_coral_missing(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="Coral CLI not found"):
        ensure_coral_available()

def test_ok_when_coral_present(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/coral")
    ensure_coral_available()  # no raise
