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
        width: 80;
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

    #status-display {
        text-align: center;
        margin-bottom: 2;
        padding: 1;
        background: $panel;
        border: solid $primary;
    }

    .info-section {
        margin-bottom: 2;
        padding: 1;
        background: $panel;
    }

    .info-item {
        margin: 0 0 1 0;
    }

    Button {
        width: 100%;
        margin: 1 0;
    }
    """

    def __init__(self, droplet: dict):
        super().__init__()
        self.droplet = droplet
        self.droplet_id = droplet.get("id")
        self.server_name = droplet.get("name", "Unknown")

        # Extract IP address
        self.ip_address = "Pending..."
        for network in droplet.get("networks", {}).get("v4", []):
            if network.get("type") == "public":
                self.ip_address = network.get("ip_address", "Pending...")
                break

    def compose(self) -> ComposeResult:
        """Compose the server detail view."""
        yield Header()
        with Container(id="detail-container"):
            yield Static(f"Server: {self.server_name}", id="title")

            # Status display
            status = self.droplet.get("status", "unknown")
            status_color = "green" if status == "active" else "yellow" if status == "new" else "red"
            yield Static(f"Status: [{status_color}]{status.upper()}[/]", id="status-display")

            # Server information
            with Container(classes="info-section"):
                yield Static("[bold]Connection Info:[/]", classes="info-item")
                yield Static(f"IP Address: {self.ip_address}", classes="info-item")
                yield Static("Port: 25565 (default)", classes="info-item")
                if self.ip_address != "Pending...":
                    yield Static(
                        f"[dim]Connect with: {self.ip_address}:25565[/]", classes="info-item"
                    )

            # Droplet details
            with Container(classes="info-section"):
                yield Static("[bold]Droplet Details:[/]", classes="info-item")
                yield Static(
                    f"Region: {self.droplet.get('region', {}).get('slug', 'Unknown')}",
                    classes="info-item",
                )
                yield Static(
                    f"Size: {self.droplet.get('size', {}).get('slug', 'Unknown')}",
                    classes="info-item",
                )
                yield Static(
                    f"Memory: {self.droplet.get('memory', 'Unknown')} MB", classes="info-item"
                )
                yield Static(f"vCPUs: {self.droplet.get('vcpus', 'Unknown')}", classes="info-item")
                yield Static(f"Disk: {self.droplet.get('disk', 'Unknown')} GB", classes="info-item")

            # Control buttons
            yield Static("[bold]Server Controls:[/]", classes="info-item")
            if status == "active":
                yield Button("Power Off", variant="warning", id="poweroff-btn")
                yield Button("Reboot", variant="default", id="reboot-btn")
            else:
                yield Button("Power On", variant="success", id="poweron-btn")

            yield Button("Delete Server", variant="error", id="delete-btn")
            yield Button("Refresh", variant="default", id="refresh-btn")
            yield Button("Back", variant="primary", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        """Refresh server status when screen loads."""
        self.refresh_server()

    def refresh_server(self) -> None:
        """Refresh server information."""
        self.run_worker(self.fetch_server_status(), exclusive=True)

    async def fetch_server_status(self) -> None:
        """Fetch current server status from DigitalOcean."""
        try:
            from ..services.digitalocean import DigitalOceanService

            do_service = DigitalOceanService(self.app.settings)
            updated_droplet = await do_service.get_droplet(self.droplet_id)

            # Update droplet data
            self.droplet = updated_droplet

            # Refresh the screen
            await self.recompose()

        except Exception as e:
            self.app.notify(f"Error refreshing server: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "refresh-btn":
            self.refresh_server()
        elif event.button.id == "poweron-btn":
            self.run_worker(self.power_on())
        elif event.button.id == "poweroff-btn":
            self.run_worker(self.power_off())
        elif event.button.id == "reboot-btn":
            self.run_worker(self.reboot())
        elif event.button.id == "delete-btn":
            self.run_worker(self.delete_server())

    async def power_on(self) -> None:
        """Power on the server."""
        try:
            from ..services.digitalocean import DigitalOceanService

            self.app.notify(f"Powering on {self.server_name}...")
            do_service = DigitalOceanService(self.app.settings)
            await do_service.power_on(self.droplet_id)
            self.app.notify(f"Power on command sent to {self.server_name}", severity="information")

            # Refresh after a delay
            import asyncio

            await asyncio.sleep(2)
            self.refresh_server()

        except Exception as e:
            self.app.notify(f"Error powering on server: {e}", severity="error")

    async def power_off(self) -> None:
        """Power off the server."""
        try:
            from ..services.digitalocean import DigitalOceanService

            self.app.notify(f"Powering off {self.server_name}...")
            do_service = DigitalOceanService(self.app.settings)
            await do_service.power_off(self.droplet_id)
            self.app.notify(f"Power off command sent to {self.server_name}", severity="warning")

            # Refresh after a delay
            import asyncio

            await asyncio.sleep(2)
            self.refresh_server()

        except Exception as e:
            self.app.notify(f"Error powering off server: {e}", severity="error")

    async def reboot(self) -> None:
        """Reboot the server."""
        try:
            from ..services.digitalocean import DigitalOceanService

            self.app.notify(f"Rebooting {self.server_name}...")
            do_service = DigitalOceanService(self.app.settings)
            await do_service.reboot(self.droplet_id)
            self.app.notify(f"Reboot command sent to {self.server_name}", severity="information")

            # Refresh after a delay
            import asyncio

            await asyncio.sleep(2)
            self.refresh_server()

        except Exception as e:
            self.app.notify(f"Error rebooting server: {e}", severity="error")

    async def delete_server(self) -> None:
        """Delete the server."""
        try:
            from ..services.digitalocean import DigitalOceanService

            self.app.notify(f"Deleting {self.server_name}...", severity="warning")
            do_service = DigitalOceanService(self.app.settings)
            await do_service.delete_droplet(self.droplet_id)
            self.app.notify(f"Server {self.server_name} deleted", severity="error")

            # Go back to server list
            self.app.pop_screen()

        except Exception as e:
            self.app.notify(f"Error deleting server: {e}", severity="error")
