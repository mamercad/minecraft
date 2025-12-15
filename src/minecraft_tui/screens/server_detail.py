"""Server detail screen."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Label, Static


class ConfirmDeleteModal(ModalScreen):
    """Modal dialog to confirm server deletion."""

    BINDINGS = [
        # Vi-style navigation
        Binding("j", "focus_next", "Focus Next", show=False),
        Binding("k", "focus_previous", "Focus Previous", show=False),
    ]

    CSS = """
    ConfirmDeleteModal {
        align: center middle;
    }

    #dialog {
        width: 60%;
        max-width: 80;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 2;
    }

    #question {
        text-align: center;
        margin-bottom: 1;
        color: $error;
    }

    #warning {
        text-align: center;
        margin-bottom: 2;
        color: $warning;
    }

    #buttons {
        height: auto;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, server_name: str):
        super().__init__()
        self.server_name = server_name

    def compose(self) -> ComposeResult:
        """Compose the confirmation dialog."""
        with Container(id="dialog"):
            yield Label(
                f"Are you sure you want to delete server '{self.server_name}'?",
                id="question",
            )
            yield Label(
                "This will permanently destroy the droplet and all data.",
                id="warning",
            )
            with Horizontal(id="buttons"):
                yield Button("Cancel", variant="default", id="cancel")
                yield Button("Delete", variant="error", id="confirm")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)


class ServerDetailScreen(Screen):
    """Screen showing details of a specific server."""

    BINDINGS = [
        # Vi-style navigation
        Binding("j", "focus_next", "Focus Next", show=False),
        Binding("k", "focus_previous", "Focus Previous", show=False),
        Binding("escape", "back", "Back", priority=True),
    ]

    CSS = """
    ServerDetailScreen {
        height: 100%;
    }

    #detail-container {
        width: 100%;
        height: 100%;
        border: solid $accent;
        padding: 2;
        background: $surface;
        overflow-y: auto;
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
                    f"Size: {self.droplet.get('size', {}).get('slug', 'Unknown')}",
                    classes="info-item",
                )
                yield Static(
                    f"Region: {self.droplet.get('region', {}).get('slug', 'Unknown')}",
                    classes="info-item",
                )
                yield Static(f"vCPUs: {self.droplet.get('vcpus', 'Unknown')}", classes="info-item")
                yield Static(
                    f"Memory: {self.droplet.get('memory', 'Unknown')} MB", classes="info-item"
                )
                yield Static(f"Disk: {self.droplet.get('disk', 'Unknown')} GB", classes="info-item")

            # Control buttons
            yield Static("[bold]Server Controls:[/]", classes="info-item")
            if status == "active":
                yield Button("View Console", variant="success", id="console-btn")
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

            # Update IP address
            self.ip_address = "Pending..."
            for network in updated_droplet.get("networks", {}).get("v4", []):
                if network.get("type") == "public":
                    self.ip_address = network.get("ip_address", "Pending...")
                    break

            # Refresh the display by updating widgets
            status = updated_droplet.get("status", "unknown")
            status_color = "green" if status == "active" else "yellow" if status == "new" else "red"
            self.query_one("#status-display", Static).update(f"Status: [{status_color}]{status.upper()}[/]")

            self.app.notify("Server status refreshed", severity="information")

        except Exception as e:
            self.app.notify(f"Error refreshing server: {e}", severity="error")

    def action_back(self) -> None:
        """Handle back action (Escape key)."""
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "back-btn":
            self.action_back()
        elif event.button.id == "refresh-btn":
            self.refresh_server()
        elif event.button.id == "console-btn":
            self.open_console()
        elif event.button.id == "poweron-btn":
            self.run_worker(self.power_on())
        elif event.button.id == "poweroff-btn":
            self.run_worker(self.power_off())
        elif event.button.id == "reboot-btn":
            self.run_worker(self.reboot())
        elif event.button.id == "delete-btn":
            self.confirm_delete()

    def open_console(self) -> None:
        """Open server console screen."""
        from pathlib import Path

        from .server_console import ServerConsoleScreen

        # Try to find a valid SSH private key
        ssh_private_key = None

        # First, check if the default key exists
        default_key = self.app.settings.ssh_private_key_path
        if default_key and Path(default_key).exists():
            ssh_private_key = str(default_key)
        else:
            # Fall back to discovering available keys
            ssh_dir = Path.home() / ".ssh"
            if ssh_dir.exists():
                for pub_key in sorted(ssh_dir.glob("*.pub")):
                    private_key = pub_key.parent / pub_key.stem
                    if private_key.exists():
                        ssh_private_key = str(private_key)
                        break

        if not ssh_private_key:
            self.app.notify(
                "No valid SSH key found. Please configure SSH_PRIVATE_KEY_PATH in settings.",
                severity="error",
            )
            return

        self.app.push_screen(ServerConsoleScreen(self.droplet, ssh_private_key))

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

    def confirm_delete(self) -> None:
        """Show confirmation dialog before deleting."""

        async def handle_delete_confirmation(confirmed: bool) -> None:
            """Handle the result of the delete confirmation."""
            if confirmed:
                await self.delete_server()

        self.app.push_screen(ConfirmDeleteModal(self.server_name), handle_delete_confirmation)

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
