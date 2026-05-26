from reef.observability import trace


def test_disabled_by_default_no_output(capsys):
    # Don't call enable(); module-level state should be disabled (or honor the order of tests).
    # To make this robust regardless of test order, force-disable via the module attribute.
    trace._enabled = False
    trace.you("hello")
    trace.reef("hi")
    trace.tool_call("write_memory", {"key": "x"})
    trace.coral_sql("SELECT 1")
    trace.info("starting up")
    captured = capsys.readouterr()
    assert captured.out == ""


def test_enable_then_lines_print(capsys):
    trace._enabled = False
    trace.enable()
    try:
        trace.you("hello there")
        trace.reef("hi back")
        trace.tool_call("reef_write_memory", {"key": "mornings", "value": "brief"})
        trace.tool_response("reef_write_memory", "Remembered: mornings = brief")
        trace.coral_sql("SELECT 1 AS n")
        trace.coral_result("1 row(s)")
        trace.info("ready")
        out = capsys.readouterr().out
        assert "[you]" in out and "hello there" in out
        assert "[reef]" in out and "hi back" in out
        assert "tool→" in out and "reef_write_memory" in out and "mornings" in out
        assert "tool←" in out and "Remembered" in out
        assert "[coral]" in out and "SELECT 1 AS n" in out
        assert "coral←" in out and "1 row(s)" in out
        assert "[info]" in out and "ready" in out
    finally:
        trace._enabled = False  # leave the module disabled for other tests


def test_skips_empty_transcripts(capsys):
    trace._enabled = False
    trace.enable()
    try:
        trace.you("")
        trace.you("   ")
        trace.reef(None)  # type: ignore[arg-type]
        assert capsys.readouterr().out == ""
    finally:
        trace._enabled = False
