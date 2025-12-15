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
        margin-bottom: 1;
    }

    #account-info {
        text-align: center;
        color: $text-muted;
        margin-bottom: 2;
        padding: 1;
        background: $panel;
        border: solid $primary;
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
            yield Static("Loading account info...", id="account-info")
            yield Button("Create New Server", variant="primary", id="create-btn")
            yield Button("View Servers", variant="default", id="view-btn")
            yield Button("Quit", variant="error", id="quit-btn")
        yield Footer()

    def on_mount(self) -> None:
        """Fetch account info when screen loads."""
        self.run_worker(self.fetch_account_info(), exclusive=True)

    async def fetch_account_info(self) -> None:
        """Fetch and display DigitalOcean account information."""
        account_widget = self.query_one("#account-info", Static)

        try:
            from ..services.digitalocean import DigitalOceanService

            do_service = DigitalOceanService(self.app.settings)
            account = await do_service.get_account_info()

            # Format account info nicely
            info_parts = [f"Account: {account['email']}"]

            if account.get("team"):
                info_parts.append(f"Team: {account['team']}")

            info_parts.extend(
                [
                    f"Droplet Limit: {account['droplet_limit']}",
                    f"Status: {account['status']}",
                ]
            )

            if account["email_verified"]:
                info_parts.append("✓ Email Verified")

            account_widget.update(" | ".join(info_parts))

        except Exception as e:
            account_widget.update(f"⚠ Could not load account info: {e}")

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
