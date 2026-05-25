"""Snapshot live Coral sources to JSONL for offline/deterministic demo (PRD D6).
Usage: uv run python scripts/snapshot.py [out_dir]
Snapshots GitHub now; add email/calendar/gcal/gmail queries here once those sources are connected."""
import sys
from reef.snapshot.runner import snapshot_query

DEFAULT_OUT = "coral/snapshots"

JOBS = [
    # (source_name, table, SQL) — extend as live sources are connected.
    ("github", "open_pulls",
     "SELECT number, title, state FROM github.pulls WHERE owner='NarayanaSabari' AND repo='Reef' AND state='open' LIMIT 50"),
]


def main(out_root: str = DEFAULT_OUT) -> None:
    for name, table, sql in JOBS:
        path = snapshot_query(name, table, sql, out_root)
        print(f"snapshot: {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT)
