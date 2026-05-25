import shutil

from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters


def ensure_coral_available() -> None:
    """Raise a clear error if the `coral` CLI isn't on PATH (it's spawned for MCP)."""
    if shutil.which("coral") is None:
        raise RuntimeError(
            "Coral CLI not found on PATH. Install it (brew install withcoral/tap/coral) "
            "and ensure it is on PATH before starting Reef."
        )


def build_coral_toolset() -> McpToolset:
    """ADK MCP toolset backed by `coral mcp-stdio` (read-only SQL over the user's sources)."""
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(command="coral", args=["mcp-stdio"])
        )
    )
