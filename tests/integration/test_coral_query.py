"""Integration test: prove the agent's Coral McpToolset can EXECUTE a SQL query.

Invocation path: direct ADK – `await sql_tool.run_async(args={"sql": ...}, tool_context=...)`
A minimal InvocationContext is constructed with InMemorySessionService and a throwaway
Session; no real agent runtime or Gemini call is required.

The `sql` tool's input parameter is named "sql" (confirmed from the raw MCP tool's
inputSchema: `{"type": "object", "required": ["sql"], ...}`).
"""
import shutil
import json
import pytest

from reef.agent.coral import build_coral_toolset
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.sessions.session import Session
from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools import ToolContext

pytestmark = pytest.mark.integration


@pytest.mark.skipif(shutil.which("coral") is None, reason="coral CLI not installed")
async def test_coral_sql_tool_executes_query():
    """Build the Coral toolset, locate the sql tool, run SELECT 1 AS n, assert result."""
    toolset = build_coral_toolset()
    try:
        tools = await toolset.get_tools()

        # Locate the sql tool
        sql_tool = next((t for t in tools if t.name == "sql"), None)
        assert sql_tool is not None, "Expected a 'sql' tool in Coral toolset"

        # Confirm the input schema declares a 'sql' parameter
        input_schema = sql_tool.raw_mcp_tool.inputSchema
        assert "sql" in input_schema.get("properties", {}), (
            f"Expected 'sql' property in inputSchema, got: {input_schema}"
        )

        # Build a minimal InvocationContext (no real agent runtime needed)
        session = Session(id="reef-test-session", app_name="reef-test", user_id="test-user")
        session_svc = InMemorySessionService()
        inv_ctx = InvocationContext(
            session_service=session_svc,
            invocation_id="reef-test-invocation-1",
            session=session,
        )
        tool_ctx = ToolContext(invocation_context=inv_ctx)

        # Execute a trivial read-only query
        result = await sql_tool.run_async(
            args={"sql": "SELECT 1 AS n"},
            tool_context=tool_ctx,
        )

        # result is a dict: {"content": [...], "structuredContent": {"rows": [...]}, "isError": bool}
        assert isinstance(result, dict), f"Expected dict result, got {type(result)}"
        assert not result.get("isError"), f"Tool returned an error: {result}"

        # Prefer structuredContent if present; fall back to parsing the text content
        structured = result.get("structuredContent")
        if structured is not None:
            rows = structured.get("rows", [])
        else:
            # Parse the text payload
            content = result.get("content", [])
            assert content, f"No content in result: {result}"
            text = content[0].get("text", "")
            parsed = json.loads(text)
            rows = parsed.get("rows", [])

        assert len(rows) >= 1, f"Expected at least one row, got: {rows}"
        first_row = rows[0]
        assert int(first_row.get("n", -1)) == 1, (
            f"Expected row[0].n == 1, got: {first_row}"
        )
    finally:
        await toolset.close()
