def test_main_module_exposes_async_main():
    import inspect

    from reef.app import main
    assert inspect.iscoroutinefunction(main.main)
