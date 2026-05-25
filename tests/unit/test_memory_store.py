import pytest
from reef.memory.store import MemoryStore, Memory

@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "reef.db")

async def test_write_then_read_back(db_path):
    store = MemoryStore(db_path)
    await store.init()
    await store.write("preference", "mornings", "brief")
    assert await store.all() == [Memory(kind="preference", key="mornings", value="brief")]

async def test_write_upserts_same_key(db_path):
    store = MemoryStore(db_path)
    await store.init()
    await store.write("preference", "mornings", "brief")
    await store.write("preference", "mornings", "very brief")
    mems = await store.all()
    assert len(mems) == 1 and mems[0].value == "very brief"

async def test_persists_across_restart(db_path):
    store1 = MemoryStore(db_path)
    await store1.init()
    await store1.write("preference", "mornings", "brief")
    store2 = MemoryStore(db_path)
    await store2.init()
    assert await store2.all() == [Memory(kind="preference", key="mornings", value="brief")]
