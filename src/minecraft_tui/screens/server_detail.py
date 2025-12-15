"""Server detail screen."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static


class ServerDetailScreen(Screen):
    """Screen showing details of a specific server."""

    CSS = """
    ServerDetailScreen {
        align: center middle;
    }

    #detail-container {
        width: 70;
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

    .info-item {
        margin: 0 0 1 0;
    }

    Button {
        width: 100%;
        margin: 1 0;
    }
    """

    def __init__(self, server_name: str):
        super().__init__()
        self.server_name = server_name

    def compose(self) -> ComposeResult:
        """Compose the server detail view."""
        yield Header()
        with Container(id="detail-container"):
            yield Static(f"Server: {self.server_name}", id="title")

            yield Static("Status: Running", classes="info-item")
            yield Static("IP Address: 192.168.1.100", classes="info-item")
            yield Static("Port: 25565", classes="info-item")
            yield Static("Type: Vanilla", classes="info-item")

            yield Button("Stop Server", variant="warning", id="stop-btn")
            yield Button("Restart Server", variant="default", id="restart-btn")
            yield Button("Delete Server", variant="error", id="delete-btn")
            yield Button("Back", variant="primary", id="back-btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "stop-btn":
            self.app.notify(f"Stopping {self.server_name}...")
        elif event.button.id == "restart-btn":
            self.app.notify(f"Restarting {self.server_name}...")
        elif event.button.id == "delete-btn":
            self.app.notify(f"Deleting {self.server_name}...")
