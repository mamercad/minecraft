"""Server list screen."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Static


class ServerListScreen(Screen):
    """Screen showing list of all servers."""

    CSS = """
    ServerListScreen {
        align: center middle;
    }

    #list-container {
        width: 90;
        height: auto;
        border: solid $accent;
        padding: 2;
        background: $surface;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    DataTable {
        height: 20;
        margin: 1 0;
    }

    Button {
        width: 100%;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the server list."""
        yield Header()
        with Container(id="list-container"):
            yield Static("Servers", id="title")
            yield DataTable(id="server-table")
            yield Button("Refresh", variant="default", id="refresh-btn")
            yield Button("Back", variant="primary", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the server list."""
        table = self.query_one(DataTable)
        table.add_columns("Name", "Type", "Status", "IP Address")

        # In a full implementation, this would load actual servers from DigitalOcean
        # For now, show a placeholder
        table.add_row("No servers", "-", "-", "-")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "refresh-btn":
            # Refresh server list
            self.app.notify("Refreshing server list...")
