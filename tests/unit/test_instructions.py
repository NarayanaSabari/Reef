import pytest
from reef.memory.store import MemoryStore
from reef.voice.instructions import make_instruction_provider, BASE_INSTRUCTION

@pytest.fixture
async def store(tmp_path):
    s = MemoryStore(str(tmp_path / "reef.db"))
    await s.init()
    return s

async def test_base_instruction_when_no_memories(store):
    provide = make_instruction_provider(store)
    assert await provide(None) == BASE_INSTRUCTION

async def test_injects_memories_into_instruction(store):
    await store.write("preference", "mornings", "brief")
    provide = make_instruction_provider(store)
    text = await provide(None)
    assert BASE_INSTRUCTION in text
    assert "mornings" in text and "brief" in text
