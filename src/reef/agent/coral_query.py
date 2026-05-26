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


def coral_query(sql: str) -> str:
    """Run a read-only SQL query against the user's connected Coral sources and return rows.

    Coral is a local SQL surface over the user's GitHub (table github.pulls for pull requests,
    github.requested_reviewers for review requests, github.issues, etc.) and any connected
    email/calendar sources. Always write ONE read-only SQL statement. If you need to discover
    tables, query `SELECT schema_name, table_name FROM coral.tables WHERE schema_name='<src>' LIMIT 50`.
    """
    try:
        proc = subprocess.run(
            ["coral", "sql", "--format", "json", sql],
            capture_output=True, text=True, timeout=15,
        )
    except subprocess.TimeoutExpired:
        return "Error: coral query timed out after 15 seconds."
    if proc.returncode != 0:
        return f"Error: {proc.stderr.strip() or 'coral sql failed'}"
    # Return the raw JSON rows; the model can read them directly.
    return proc.stdout.strip() or "[]"
