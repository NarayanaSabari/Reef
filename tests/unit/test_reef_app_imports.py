"""The menubar app shell imports cleanly and exposes a sync `main()` entry point.
The actual GUI run is verified manually on the user's Mac (rumps needs an NSApplication
context to truly launch)."""
import inspect


def test_reef_app_module_imports():
    import reef.shell.app  # noqa: F401
    from reef.shell.app import ReefApp, main
    assert callable(main)
    assert not inspect.iscoroutinefunction(main)   # sync entry point for project.scripts
    assert callable(ReefApp)


def test_reef_window_app_imports():
    """The window app (pywebview) module imports + exposes a sync main(),
    plus the JS-bridge API surface the new wireframe-based UI calls into."""
    import reef.shell.window_app  # noqa: F401
    from reef.shell.window_app import UI_PATH, Api, main
    assert callable(main)
    assert not inspect.iscoroutinefunction(main)
    assert callable(Api)

    # The HTML asset must exist + carry the design tokens (so a stray rename
    # of the file or a missing-from-wheel deploy is caught here).
    assert UI_PATH.is_file(), f"window.html missing at {UI_PATH}"
    html = UI_PATH.read_text(encoding="utf-8")
    assert "Instrument Serif" in html
    assert 'data-route="onboarding"' in html
    assert "route-chat" in html
    assert "sheet-backdrop" in html

    # The full JS bridge the new UI calls. Missing any of these would surface
    # as a silent JS-side reject promise — easier to catch here.
    api = Api()
    for name in (
        "init_route", "toggle_mic", "brief_now", "push_event",
        "save_profile", "complete_onboarding",
        "stub_mark_connected", "disconnect_google",
        "get_settings_snapshot", "get_startup_error",
    ):
        assert callable(getattr(api, name)), f"Api.{name} missing"

    # init_route must always include the error/voice_ok keys so the JS-side
    # banner logic can rely on them existing.
    route = api.init_route()
    assert set(["route", "step", "error", "voice_ok"]).issubset(route.keys())
    assert route["error"] is None         # nothing failed yet
    assert route["voice_ok"] is False     # async thread hasn't set it yet

    # The HTML must wire the banner so a missing api key actually surfaces.
    assert 'id="banner"' in html
    assert "showBanner" in html
    assert "get_startup_error" in html


def test_is_onboarded_sync_handles_missing_and_present(tmp_path):
    """The sync onboarded-check used by init_route must work without the
    asyncio loop running — and must not raise on a missing/empty DB."""
    from reef.shell.window_app import _is_onboarded_sync
    db = tmp_path / "reef.db"
    # missing file → False
    assert _is_onboarded_sync(str(db)) is False
    # empty file (no schema) → False (sqlite raises OperationalError, swallowed)
    db.write_bytes(b"")
    assert _is_onboarded_sync(str(db)) is False
    # populated schema + onboarded flag → True
    import sqlite3
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE memory (kind TEXT, key TEXT, value TEXT,"
            " created_at TEXT, PRIMARY KEY(kind, key))"
        )
        conn.execute(
            "INSERT INTO memory VALUES('profile','onboarded','true','now')"
        )
        conn.commit()
    assert _is_onboarded_sync(str(db)) is True


def test_cli_wrapper_in_main_is_sync():
    """The terminal-mode `reef` console script points at the sync wrapper, not async main."""
    from reef.app.main import cli, main
    assert not inspect.iscoroutinefunction(cli)
    assert inspect.iscoroutinefunction(main)       # the async one stays
