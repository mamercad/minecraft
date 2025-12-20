"""Main Textual application."""

from textual.app import App
from textual.binding import Binding

from .config import Settings


class MinecraftTUI(App):
    """Minecraft Server Manager TUI Application."""

    CSS = """
    Screen {
        height: 100%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
        Binding("question_mark", "show_readme", "Help", show=True),
        Binding("c", "show_changelog", "Changelog", show=False),
        # Vi-style navigation
        Binding("j", "focus_next", "Focus Next", show=False),
        Binding("k", "focus_previous", "Focus Previous", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.dark = True  # Start in dark mode

    def on_mount(self) -> None:
        """Initialize app on mount."""
        from .screens.splash import SplashScreen

        # Show splash screen first, then show next screen after it's dismissed
        self.push_screen(SplashScreen(), callback=self.show_next_screen)

    def show_next_screen(self, _result=None) -> None:
        """Show the appropriate screen after splash.

        Args:
            _result: Unused result from dismissed screen
        """
        from .screens.main_menu import MainMenuScreen
        from .screens.welcome import WelcomeScreen

        # Check for DIGITALOCEAN_TOKEN and push appropriate screen
        if not self.settings.digitalocean_token:
            self.push_screen(WelcomeScreen())
        else:
            self.push_screen(MainMenuScreen())

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"

    def action_show_readme(self) -> None:
        """Show README modal."""
        from .screens.docs_modal import ReadmeModal

        self.push_screen(ReadmeModal())

    def action_show_changelog(self) -> None:
        """Show Changelog modal."""
        from .screens.docs_modal import ChangelogModal

        self.push_screen(ChangelogModal())
