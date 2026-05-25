import pytest

from reef.snapshot import runner
from reef.snapshot.jsonl import read_jsonl


def test_run_coral_json_parses_rows(monkeypatch):
    class P:
        returncode = 0
        stdout = '[{"a":1},{"a":2}]'
        stderr = ""
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: P())
    assert runner.run_coral_json("SELECT 1") == [{"a": 1}, {"a": 2}]


def test_run_coral_json_raises_on_error(monkeypatch):
    class P:
        returncode = 1
        stdout = ""
        stderr = "boom"
    monkeypatch.setattr(runner.subprocess, "run", lambda *a, **k: P())
    with pytest.raises(RuntimeError, match="boom"):
        runner.run_coral_json("SELECT 1")


def test_snapshot_query_writes_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "run_coral_json", lambda sql: [{"id": "1"}, {"id": "2"}])
    p = runner.snapshot_query("demo", "things", "SELECT ...", str(tmp_path))
    assert read_jsonl(p) == [{"id": "1"}, {"id": "2"}]
