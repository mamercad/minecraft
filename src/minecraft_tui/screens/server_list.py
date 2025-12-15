"""Server list screen."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Static
from textual.widgets.data_table import RowKey


class ServerListScreen(Screen):
    """Screen showing list of all servers."""

    BINDINGS = [
        # Vi-style navigation for DataTable
        Binding("j", "cursor_down", "Move Down", show=False),
        Binding("k", "cursor_up", "Move Up", show=False),
        Binding("g", "scroll_home", "Scroll Home", show=False),
        Binding("G", "scroll_end", "Scroll End", show=False),
        Binding("escape", "back", "Back", priority=True),
    ]

    def __init__(self):
        super().__init__()
        self.droplet_map: dict[RowKey, dict] = {}  # Map row keys to droplet data
        self.auto_refresh_enabled = True  # Auto-refresh enabled by default
        self.refresh_timer = None

    CSS = """
    ServerListScreen {
        height: 100%;
    }

    #list-container {
        width: 100%;
        height: 100%;
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
        height: 1fr;
        margin: 1 0;
    }

    Button {
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the server list."""
        yield Header()
        with Container(id="list-container"):
            yield Static("Minecraft Servers", id="title")
            yield Static("Loading servers... | Auto-refresh: ON", id="status")
            yield DataTable(id="server-table", cursor_type="row")
            yield Button("Refresh", variant="default", id="refresh-btn")
            yield Button("Auto-refresh: ON", variant="success", id="toggle-refresh-btn")
            yield Button("Back", variant="primary", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the server list."""
        table = self.query_one(DataTable)
        table.add_columns("Name", "IP Address", "Size", "Region", "Status", "Created")
        self.load_servers()
        # Focus the Back button by default
        self.query_one("#back-btn", Button).focus()
        # Start auto-refresh timer (30 seconds)
        self.start_auto_refresh()

    def on_resume(self) -> None:
        """Called when returning to this screen."""
        # Refresh the server list when returning from detail view
        self.load_servers()
        # Restart auto-refresh if it was enabled
        if self.auto_refresh_enabled:
            self.start_auto_refresh()

    def start_auto_refresh(self) -> None:
        """Start the auto-refresh timer."""
        if self.auto_refresh_enabled and self.refresh_timer is None:
            # Refresh every 30 seconds
            self.refresh_timer = self.set_interval(30.0, self.auto_refresh_callback)

    def stop_auto_refresh(self) -> None:
        """Stop the auto-refresh timer."""
        if self.refresh_timer is not None:
            self.refresh_timer.stop()
            self.refresh_timer = None

    def auto_refresh_callback(self) -> None:
        """Called by the timer to auto-refresh the list."""
        if self.auto_refresh_enabled:
            self.load_servers()

    def load_servers(self) -> None:
        """Load servers from DigitalOcean."""
        self.run_worker(self.fetch_servers(), exclusive=False)

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

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the table."""
        if event.row_key in self.droplet_map:
            from .server_detail import ServerDetailScreen

            droplet = self.droplet_map[event.row_key]
            self.app.push_screen(ServerDetailScreen(droplet))

    def action_back(self) -> None:
        """Handle back action (Escape key)."""
        self.stop_auto_refresh()
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "back-btn":
            self.action_back()
        elif event.button.id == "refresh-btn":
            self.load_servers()
        elif event.button.id == "toggle-refresh-btn":
            self.toggle_auto_refresh()

    def toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh on/off."""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        button = self.query_one("#toggle-refresh-btn", Button)
        status = self.query_one("#status", Static)

        if self.auto_refresh_enabled:
            button.label = "Auto-refresh: ON"
            button.variant = "success"
            self.start_auto_refresh()
            # Update status to show auto-refresh is on
            current_status = status.renderable
            if " | Auto-refresh:" not in str(current_status):
                status.update(f"{current_status} | Auto-refresh: ON")
            else:
                status.update(str(current_status).replace("Auto-refresh: OFF", "Auto-refresh: ON"))
        else:
            button.label = "Auto-refresh: OFF"
            button.variant = "default"
            self.stop_auto_refresh()
            # Update status to show auto-refresh is off
            current_status = status.renderable
            if "Auto-refresh: ON" in str(current_status):
                status.update(str(current_status).replace("Auto-refresh: ON", "Auto-refresh: OFF"))
            elif " | Auto-refresh:" not in str(current_status):
                status.update(f"{current_status} | Auto-refresh: OFF")
