from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters


def build_coral_toolset() -> McpToolset:
    """ADK MCP toolset backed by `coral mcp-stdio` (read-only SQL over the user's sources)."""
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(command="coral", args=["mcp-stdio"])
        )
    )
