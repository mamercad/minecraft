"""Server list screen."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Static
from textual.widgets.data_table import RowKey


class ServerListScreen(Screen):
    """Screen showing list of all servers."""

    def __init__(self):
        super().__init__()
        self.droplet_map: dict[RowKey, dict] = {}  # Map row keys to droplet data

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

    #status {
        text-align: center;
        color: $text-muted;
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
            yield Static("Minecraft Servers", id="title")
            yield Static("Loading servers...", id="status")
            yield DataTable(id="server-table", cursor_type="row")
            yield Button("Refresh", variant="default", id="refresh-btn")
            yield Button("Back", variant="primary", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the server list."""
        table = self.query_one(DataTable)
        table.add_columns("Name", "IP Address", "Region", "Status", "Created")
        self.load_servers()

    def load_servers(self) -> None:
        """Load servers from DigitalOcean."""
        self.run_worker(self.fetch_servers(), exclusive=True)

    async def fetch_servers(self) -> None:
        """Fetch servers from DigitalOcean API."""
        table = self.query_one(DataTable)
        status = self.query_one("#status", Static)

        try:
            from ..services.digitalocean import DigitalOceanService

            # Clear existing rows
            table.clear()
            self.droplet_map.clear()  # Clear the droplet mapping

            status.update("Fetching servers from DigitalOcean...")

            do_service = DigitalOceanService(self.app.settings)
            droplets = await do_service.list_droplets(tag="minecraft-tui")

            if not droplets:
                status.update("No servers found")
                table.add_row("No servers found", "-", "-", "-", "-")
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

                region = droplet.get("region", {}).get("slug", "Unknown")
                status_text = droplet.get("status", "unknown")
                created_at = droplet.get("created_at", "Unknown")

                # Format created_at to just date
                if created_at != "Unknown":
                    created_at = created_at.split("T")[0]

                # Add row and store droplet data
                row_key = table.add_row(name, ip_address, region, status_text, created_at)
                self.droplet_map[row_key] = droplet

        except Exception as e:
            status.update(f"Error loading servers: {e}")
            table.clear()
            table.add_row("Error loading servers", str(e), "-", "-", "-")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the table."""
        if event.row_key in self.droplet_map:
            from .server_detail import ServerDetailScreen

            droplet = self.droplet_map[event.row_key]
            self.app.push_screen(ServerDetailScreen(droplet))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "refresh-btn":
            self.load_servers()
