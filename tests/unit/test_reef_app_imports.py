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
    """The window app (pywebview) module imports + exposes a sync main()."""
    import reef.shell.window_app  # noqa: F401
    from reef.shell.window_app import Api, main
    assert callable(main)
    assert not inspect.iscoroutinefunction(main)
    assert callable(Api)
    # Basic shape of the Api bridge:
    api = Api()
    assert hasattr(api, "toggle_mic")
    assert hasattr(api, "brief_now")
    assert hasattr(api, "push_event")


def test_cli_wrapper_in_main_is_sync():
    """The terminal-mode `reef` console script points at the sync wrapper, not async main."""
    from reef.app.main import cli, main
    assert not inspect.iscoroutinefunction(cli)
    assert inspect.iscoroutinefunction(main)       # the async one stays
