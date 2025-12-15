"""Main menu screen."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static


class MainMenuScreen(Screen):
    """Main menu screen."""

    CSS = """
    MainMenuScreen {
        align: center middle;
    }

    #menu-container {
        width: 60;
        height: auto;
        border: solid $accent;
        padding: 2;
        background: $surface;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 2;
    }

    Button {
        width: 100%;
        margin: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the main menu."""
        yield Header()
        with Container(id="menu-container"):
            yield Static("Minecraft Server Manager", id="title")
            yield Button("Create New Server", variant="primary", id="create-btn")
            yield Button("View Servers", variant="default", id="view-btn")
            yield Button("Quit", variant="error", id="quit-btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "create-btn":
            from .create_server import CreateServerScreen

            self.app.push_screen(CreateServerScreen())
        elif event.button.id == "view-btn":
            from .server_list import ServerListScreen

            self.app.push_screen(ServerListScreen())
        elif event.button.id == "quit-btn":
            self.app.exit()
