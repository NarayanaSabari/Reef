import shutil

import pytest

from reef.agent.coral import build_coral_toolset

pytestmark = pytest.mark.integration


@pytest.mark.skipif(shutil.which("coral") is None, reason="coral CLI not installed")
async def test_coral_toolset_lists_tools():
    toolset = build_coral_toolset()
    try:
        tools = await toolset.get_tools()
        assert len(tools) >= 1
    finally:
        await toolset.close()
