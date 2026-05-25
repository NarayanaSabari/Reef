"""Integration test: proves the showpiece calendar ⋈ email JOIN via real Coral."""

import pathlib
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.integration

FIX = pathlib.Path(__file__).parent.parent / "fixtures" / "coral"

EMAIL_SPEC = """name: reef_demo_email
version: 0.1.0
dsl_version: 3
backend: jsonl
tables:
  - name: messages
    description: Demo email messages.
    source:
      location: "file://{dir}/"
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

CAL_SPEC = """name: reef_demo_calendar
version: 0.1.0
dsl_version: 3
backend: jsonl
tables:
  - name: events
    description: Demo calendar events (one row per event-attendee).
    source:
      location: "file://{dir}/"
    columns:
      - name: event
        type: Utf8
      - name: start_time
        type: Utf8
      - name: attendee_email
        type: Utf8
"""

JOIN = (
    "SELECT c.event, c.attendee_email, e.subject "
    "FROM reef_demo_calendar.events c "
    "JOIN reef_demo_email.messages e ON e.from_email = c.attendee_email "
    "WHERE e.last_direction = 'inbound' AND e.is_answered = false"
)


def _coral(*args):
    return subprocess.run(["coral", *args], capture_output=True, text=True)


@pytest.mark.skipif(shutil.which("coral") is None, reason="coral CLI not installed")
def test_showpiece_calendar_email_join(tmp_path):
    """WHO AM I MEETING TODAY THAT I STILL OWE A REPLY TO?

    With the curated fixtures:
    - Sarah: inbound + unanswered  → appears in JOIN result
    - Bob:   outbound              → excluded
    - Priya: answered              → excluded
    """
    email_dir = (FIX / "email").resolve()
    cal_dir = (FIX / "calendar").resolve()

    email_spec = tmp_path / "reef_demo_email.yaml"
    cal_spec = tmp_path / "reef_demo_calendar.yaml"

    email_spec.write_text(EMAIL_SPEC.format(dir=email_dir))
    cal_spec.write_text(CAL_SPEC.format(dir=cal_dir))

    try:
        result = _coral("source", "add", "--file", str(email_spec))
        assert result.returncode == 0, f"email source add failed:\n{result.stderr}"

        result = _coral("source", "add", "--file", str(cal_spec))
        assert result.returncode == 0, f"calendar source add failed:\n{result.stderr}"

        out = _coral("sql", JOIN)
        assert out.returncode == 0, f"coral sql failed:\n{out.stderr}"

        # Sarah must appear: inbound + unanswered
        assert "sarah@acme.com" in out.stdout, f"Expected sarah@acme.com in output:\n{out.stdout}"
        assert "Design review" in out.stdout, f"Expected 'Design review' in output:\n{out.stdout}"

        # Bob must NOT appear: outbound message
        assert "bob@acme.com" not in out.stdout, f"bob@acme.com should be excluded (outbound):\n{out.stdout}"

        # Priya must NOT appear: already answered
        assert "priya@acme.com" not in out.stdout, f"priya@acme.com should be excluded (answered):\n{out.stdout}"

    finally:
        _coral("source", "remove", "reef_demo_email")
        _coral("source", "remove", "reef_demo_calendar")
