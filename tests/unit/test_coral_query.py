from reef.agent import coral_query as cq_mod
from reef.agent.coral_query import coral_query


class _Proc:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_returns_stdout_on_success(monkeypatch):
    monkeypatch.setattr(cq_mod.subprocess, "run", lambda *a, **k: _Proc(stdout='[{"n":1}]'))
    assert coral_query("SELECT 1 AS n") == '[{"n":1}]'


def test_returns_error_string_on_failure(monkeypatch):
    monkeypatch.setattr(cq_mod.subprocess, "run", lambda *a, **k: _Proc(returncode=1, stderr="bad sql"))
    out = coral_query("nope")
    assert out.startswith("Error:") and "bad sql" in out


def test_empty_result_returns_empty_array(monkeypatch):
    monkeypatch.setattr(cq_mod.subprocess, "run", lambda *a, **k: _Proc(stdout=""))
    assert coral_query("SELECT 1 WHERE FALSE") == "[]"


def test_timeout_returns_clear_error(monkeypatch):
    import subprocess
    def _raise(*a, **k):
        raise subprocess.TimeoutExpired(cmd=a[0], timeout=15)
    monkeypatch.setattr(cq_mod.subprocess, "run", _raise)
    out = coral_query("SELECT * FROM huge")
    assert "timed out" in out.lower()
