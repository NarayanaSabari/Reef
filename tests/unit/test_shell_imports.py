def test_menubar_and_hotkey_import():
    import reef.shell.hotkey  # noqa: F401
    import reef.shell.menubar  # noqa: F401
    from reef.shell.hotkey import start_hotkey
    from reef.shell.menubar import ReefMenuBar
    assert callable(start_hotkey) and ReefMenuBar is not None
