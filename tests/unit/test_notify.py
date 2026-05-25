from reef.shell import notify as notify_mod


def test_notify_invokes_osascript_with_title_and_message(monkeypatch):
    calls = []
    monkeypatch.setattr(notify_mod.subprocess, "run", lambda *a, **k: calls.append(a[0]))
    notify_mod.notify("Reef", "Morning brief ready")
    assert calls and calls[0][0] == "osascript"
    joined = " ".join(calls[0])
    assert "Reef" in joined and "Morning brief ready" in joined


def test_notify_escapes_double_quotes(monkeypatch):
    calls = []
    monkeypatch.setattr(notify_mod.subprocess, "run", lambda *a, **k: calls.append(a[0]))
    notify_mod.notify("T", 'he said "hi"')
    assert calls  # does not raise
