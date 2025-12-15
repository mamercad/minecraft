"""Main Textual application."""

from textual.app import App
from textual.binding import Binding

from .config import Settings


class MinecraftTUI(App):
    """Minecraft Server Manager TUI Application."""

    CSS = """
    Screen {
        align: center middle;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    def __init__(self):
        super().__init__()
        self.settings = Settings()

    def on_mount(self) -> None:
        """Initialize app on mount."""
        from .screens.main_menu import MainMenuScreen
        from .screens.welcome import WelcomeScreen

        # Check for DIGITALOCEAN_TOKEN
        if not self.settings.digitalocean_token:
            self.push_screen(WelcomeScreen())
        else:
            self.push_screen(MainMenuScreen())

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark
