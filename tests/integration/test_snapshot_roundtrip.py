import shutil
import subprocess
import pathlib

import pytest
from reef.snapshot.runner import snapshot_query
from reef.snapshot.jsonl import read_jsonl

pytestmark = pytest.mark.integration

SQL = "SELECT schema_name, table_name FROM coral.tables WHERE schema_name='github' ORDER BY table_name LIMIT 5"


@pytest.mark.skipif(shutil.which("coral") is None, reason="coral not installed")
def test_snapshot_github_then_read_back_via_coral(tmp_path):
    path = snapshot_query("snap_github", "tables", SQL, str(tmp_path))
    rows = read_jsonl(path)
    assert len(rows) == 5 and "table_name" in rows[0]   # real GitHub data captured

    # round-trip: register the snapshot dir as a jsonl Coral source and query it
    snap_dir = pathlib.Path(path).parent.resolve()
    spec = tmp_path / "snap_src.yaml"
    spec.write_text(f'''name: reef_snap_test
version: 0.1.0
dsl_version: 3
backend: jsonl
tables:
  - name: tables
    description: Snapshot of github catalog rows.
    source:
      location: "file://{snap_dir}/"
    columns:
      - name: schema_name
        type: Utf8
      - name: table_name
        type: Utf8
''')
    try:
        assert subprocess.run(["coral", "source", "add", "--file", str(spec)]).returncode == 0
        out = subprocess.run(
            ["coral", "sql", "--format", "json", "SELECT count(*) AS c FROM reef_snap_test.tables"],
            capture_output=True, text=True,
        )
        assert out.returncode == 0, out.stderr
        assert '"c":5' in out.stdout.replace(" ", "")
    finally:
        subprocess.run(["coral", "source", "remove", "reef_snap_test"])
