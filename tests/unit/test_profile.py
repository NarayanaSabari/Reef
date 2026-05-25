import pytest

from reef.memory.store import MemoryStore
from reef.onboarding.profile import save_profile
from reef.voice.instructions import make_instruction_provider


@pytest.fixture
async def store(tmp_path):
    s = MemoryStore(str(tmp_path / "reef.db"))
    await s.init()
    return s

async def test_save_profile_persists_rows(store):
    await save_profile(store, name="Venkat", aliases=["QuantiPeak", "Neuskale"],
                       github_owner="NarayanaSabari", github_repo="Reef")
    got = {m.key: m.value for m in await store.all()}
    assert got["name"] == "Venkat"
    assert "QuantiPeak" in got["aliases"]
    assert got["github_owner"] == "NarayanaSabari"
    assert got["github_repo"] == "Reef"

async def test_profile_flows_into_instruction(store):
    await save_profile(store, name="Venkat", aliases=[], github_owner="NarayanaSabari", github_repo="Reef")
    text = await make_instruction_provider(store)(None)
    assert "Venkat" in text and "NarayanaSabari" in text and "Reef" in text
