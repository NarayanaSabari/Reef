import rumps


class ReefMenuBar(rumps.App):
    """Menu-bar entry point. Live behavior verified on the user's Mac."""
    def __init__(self, on_talk):
        super().__init__("Reef", quit_button="Quit")
        self._on_talk = on_talk
        self.menu = [rumps.MenuItem("Talk to Reef", callback=self._talk)]

    def _talk(self, _sender):
        self._on_talk()

    def run_app(self) -> None:  # thin wrapper; not called in tests
        self.run()
