from reef.snapshot.jsonl import write_jsonl, read_jsonl

def test_write_then_read_roundtrip(tmp_path):
    p = str(tmp_path / "snap.jsonl")
    rows = [{"id": "1", "subject": "hi"}, {"id": "2", "subject": "yo"}]
    write_jsonl(p, rows)
    assert read_jsonl(p) == rows

def test_read_ignores_blank_lines(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text('{"a": 1}\n\n{"a": 2}\n')
    assert read_jsonl(str(p)) == [{"a": 1}, {"a": 2}]
