"""Register the calendar + email JSONL fixtures as Coral sources for the showpiece JOIN.

Run once, then ask Reef: 'who am I meeting today that I still owe a reply to?'
The agent will issue ONE coral_query that JOINs demo_calendar.events with
demo_email.messages on attendee email - the demo's punchline working through voice.

Idempotent: removes prior demo_email / demo_calendar registrations and re-adds them
pointed at the fixture directories in this repo.

Usage:
    uv run python scripts/register_demo_sources.py
"""
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).parent.parent.resolve()
EMAIL_DIR = REPO / "tests" / "fixtures" / "coral" / "email"
CAL_DIR = REPO / "tests" / "fixtures" / "coral" / "calendar"

EMAIL_SPEC = f"""name: demo_email
version: 0.1.0
dsl_version: 3
backend: jsonl
tables:
  - name: messages
    description: Demo email messages for the showpiece cross-source JOIN.
    source:
      location: "file://{EMAIL_DIR}/"
    columns:
      - name: from_email
        type: Utf8
      - name: subject
        type: Utf8
      - name: last_direction
        type: Utf8
      - name: is_answered
        type: Boolean
"""

CAL_SPEC = f"""name: demo_calendar
version: 0.1.0
dsl_version: 3
backend: jsonl
tables:
  - name: events
    description: Demo calendar events (one row per event-attendee, denormalized).
    source:
      location: "file://{CAL_DIR}/"
    columns:
      - name: event
        type: Utf8
      - name: start_time
        type: Utf8
      - name: attendee_email
        type: Utf8
"""


def _coral(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["coral", *args], capture_output=True, text=True)


def register(name: str, spec_yaml: str) -> bool:
    _coral("source", "remove", name)   # idempotent
    spec_path = REPO / f".reef-{name}.yaml"
    spec_path.write_text(spec_yaml)
    try:
        result = _coral("source", "add", "--file", str(spec_path))
    finally:
        spec_path.unlink(missing_ok=True)
    if result.returncode != 0:
        print(f"FAILED to add {name}: {result.stderr.strip()}", file=sys.stderr)
        return False
    print(f"+ added {name}")
    return True


def main() -> int:
    if not EMAIL_DIR.exists() or not CAL_DIR.exists():
        print(f"fixture dirs missing under {REPO}/tests/fixtures/coral/", file=sys.stderr)
        return 2
    ok = True
    ok &= register("demo_email", EMAIL_SPEC)
    ok &= register("demo_calendar", CAL_SPEC)
    if ok:
        print()
        print("Done. Now:")
        print("  uv run python -m reef.app.main")
        print('  Say: "who am I meeting today that I still owe a reply to?"')
        print()
        print("To remove later: coral source remove demo_email; coral source remove demo_calendar")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
