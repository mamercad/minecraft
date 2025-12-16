"""Main menu screen."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Static
from textual.widgets.data_table import RowKey


class MainMenuScreen(Screen):
    """Main menu screen."""

    BINDINGS = [
        # Vi-style navigation
        Binding("j", "focus_next", "Focus Next", show=False),
        Binding("k", "focus_previous", "Focus Previous", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.droplet_map: dict[RowKey, dict] = {}  # Map row keys to droplet data

    CSS = """
    MainMenuScreen {
        height: 100%;
    }

    #main-layout {
        width: 100%;
        height: 100%;
    }

    #content-layout {
        width: 100%;
        height: auto;
        max-height: 23;
        border: solid $accent;
        padding: 2;
        background: $surface;
        margin-bottom: 1;
    }

    #creeper-art {
        width: auto;
        height: auto;
        max-height: 23;
        color: $success;
        text-style: bold;
        padding: 1 2;
        margin-right: 2;
    }

    #menu-section {
        width: 1fr;
        height: auto;
        max-height: 23;
        padding: 1;
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

    #server-list-container {
        width: 100%;
        height: 1fr;
        min-height: 10;
        border: solid $accent;
        padding: 2;
        background: $surface;
    }

    #server-list-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #server-status {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    DataTable {
        height: 1fr;
    }

    Button {
        margin: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the main menu."""
        # Minecraft Creeper ASCII art
        creeper = """
    ████████████████
    ████████████████
    ██          ██
    ██  ████  ████
    ██  ████  ████
    ██          ██
    ████████████████
    ██  ████████  ██
    ██  ██    ██  ██
    ██████    ██████
    ████████████████
        """

        yield Header()
        with Vertical(id="main-layout"):
            with Horizontal(id="content-layout"):
                yield Static(creeper, id="creeper-art")
                with Vertical(id="menu-section"):
                    yield Static("Minecraft Server Manager", id="title")
                    yield Static("Loading account info...", id="account-info")
                    with Horizontal():
                        yield Button("Create New Server", variant="primary", id="create-btn")
                        yield Button("Quit", variant="error", id="quit-btn")
            with Container(id="server-list-container"):
                yield Static("Your Servers", id="server-list-title")
                yield Static("Loading servers...", id="server-status")
                yield DataTable(id="server-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        """Fetch account info and servers when screen loads."""
        # Initialize DataTable columns
        table = self.query_one(DataTable)
        table.add_columns("Name", "IP Address", "Size", "Region", "Status", "Created")
        # Fetch account info and servers
        self.run_worker(self.fetch_account_info(), exclusive=True)
        self.run_worker(self.fetch_servers(), exclusive=False)

    def on_resume(self) -> None:
        """Called when returning to this screen."""
        # Refresh the server list when returning from detail view
        self.run_worker(self.fetch_servers(), exclusive=False)

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

    async def fetch_servers(self) -> None:
        """Fetch servers from DigitalOcean API."""
        table = self.query_one(DataTable)
        status = self.query_one("#server-status", Static)

        try:
            from ..services.digitalocean import DigitalOceanService

            # Clear existing rows
            table.clear()
            self.droplet_map.clear()

            status.update("Fetching servers from DigitalOcean...")

            do_service = DigitalOceanService(self.app.settings)
            droplets = await do_service.list_droplets(tag="minecraft-tui")

            if not droplets:
                status.update("No servers found")
                table.add_row("No servers found", "-", "-", "-", "-", "-")
                return

            status.update(f"Found {len(droplets)} server(s)")

            # Add each droplet to the table
            for droplet in droplets:
                name = droplet.get("name", "Unknown")

                # Get IP address
                ip_address = "Pending..."
                for network in droplet.get("networks", {}).get("v4", []):
                    if network.get("type") == "public":
                        ip_address = network.get("ip_address", "Pending...")
                        break

                size = droplet.get("size", {}).get("slug", "Unknown")
                region = droplet.get("region", {}).get("slug", "Unknown")
                status_text = droplet.get("status", "unknown")
                created_at = droplet.get("created_at", "Unknown")

                # Format created_at to just date
                if created_at != "Unknown":
                    created_at = created_at.split("T")[0]

                # Add row and store droplet data
                row_key = table.add_row(name, ip_address, size, region, status_text, created_at)
                self.droplet_map[row_key] = droplet

        except Exception as e:
            status.update(f"Error loading servers: {e}")
            table.clear()
            table.add_row("Error loading servers", str(e), "-", "-", "-", "-")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "create-btn":
            from .create_server import CreateServerScreen

            self.app.push_screen(CreateServerScreen())
        elif event.button.id == "quit-btn":
            self.app.exit()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the server table."""
        if event.row_key in self.droplet_map:
            from .server_detail import ServerDetailScreen

            droplet = self.droplet_map[event.row_key]
            self.app.push_screen(ServerDetailScreen(droplet))
