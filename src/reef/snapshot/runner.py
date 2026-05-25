import json
import subprocess
from pathlib import Path
from reef.snapshot.jsonl import write_jsonl


def run_coral_json(sql: str) -> list[dict]:
    """Run a Coral SQL query and return rows as dicts (via `coral sql --format json`)."""
    proc = subprocess.run(["coral", "sql", "--format", "json", sql],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"coral sql failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout or "[]")


def snapshot_query(name: str, table: str, sql: str, out_root: str) -> str:
    """Snapshot a Coral query to <out_root>/<name>/<table>.jsonl. Returns the file path."""
    out_dir = Path(out_root) / name
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = run_coral_json(sql)
    path = out_dir / f"{table}.jsonl"
    write_jsonl(str(path), rows)
    return str(path)
