"""Single-tool wrapper around the Coral CLI for the voice agent.

Why this exists: ADK's `McpToolset` exposes Coral as 5 separate tools (sql, list_catalog,
search_catalog, describe_table, list_columns) to the model. Combined with our memory tools
+ clock + timer that's 10 tools total - preview Live models become flaky after a turn or
two with that many. This wrapper collapses Coral to a SINGLE function tool that runs SQL
via `coral sql --format json` in a subprocess, so the voice agent sees only 6 tools and
multi-turn stability holds.

Trade-off: the model loses catalog-discovery tools (list_catalog etc.). The agent
instruction tells it the relevant table names directly, which is enough for the demo.
The standalone McpToolset (src/reef/agent/coral.py) is still used by the integration
test that verifies the MCP transport works.
"""
import json
import subprocess

from reef.observability import trace


def coral_query(sql: str) -> str:
    """Run a read-only SQL query against the user's connected Coral sources and return rows.

    Coral is a local SQL surface over the user's GitHub (table github.pulls for pull requests,
    github.requested_reviewers for review requests, github.issues, etc.) and any connected
    email/calendar sources. Always write ONE read-only SQL statement. If you need to discover
    tables, query `SELECT schema_name, table_name FROM coral.tables WHERE schema_name='<src>' LIMIT 50`.
    """
    trace.coral_sql(sql)
    try:
        proc = subprocess.run(
            ["coral", "sql", "--format", "json", sql],
            capture_output=True, text=True, timeout=15,
        )
    except subprocess.TimeoutExpired:
        msg = "Error: coral query timed out after 15 seconds."
        trace.coral_result(msg)
        return msg
    if proc.returncode != 0:
        msg = f"Error: {proc.stderr.strip() or 'coral sql failed'}"
        trace.coral_result(msg[:120])
        return msg
    result = proc.stdout.strip() or "[]"
    # Summarize row count if the output is a JSON array.
    try:
        rows = json.loads(result)
        trace.coral_result(f"{len(rows)} row(s)" if isinstance(rows, list) else "ok")
    except Exception:
        trace.coral_result("ok")
    return result
