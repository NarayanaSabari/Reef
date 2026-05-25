import pytest
from google.adk.sessions import DatabaseSessionService

pytestmark = pytest.mark.integration


async def test_session_survives_a_new_service_instance(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'reef.db'}"
    svc1 = DatabaseSessionService(db_url=db_url)
    await svc1.create_session(app_name="reef", user_id="local", session_id="voice")
    # simulate a restart: a brand-new service on the same DB file
    svc2 = DatabaseSessionService(db_url=db_url)
    restored = await svc2.get_session(app_name="reef", user_id="local", session_id="voice")
    assert restored is not None
    assert restored.id == "voice"
