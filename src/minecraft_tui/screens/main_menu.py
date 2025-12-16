"""Main menu screen."""

import pyperclip
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, DataTable, Footer, Header, Label, Static
from textual.widgets.data_table import RowKey


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
        self.selected_droplet: dict | None = None  # Currently selected droplet
        self.selected_droplet_id: int | None = None
        self.selected_server_name: str | None = None
        self.selected_ip_address: str | None = None

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
        height: auto;
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
        height: auto;
        max-height: 15;
    }

    Button {
        margin: 1 0;
    }

    #detail-container {
        width: 100%;
        height: 1fr;
        border: solid $primary;
        padding: 2;
        background: $surface;
        overflow-y: auto;
        display: none;
    }

    #detail-title {
        text-align: center;
        text-style: bold;
        color: $primary;
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

    #detail-buttons {
        margin-top: 1;
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

            # Detail pane (hidden by default)
            with Container(id="detail-container"):
                yield Static("Server Details", id="detail-title")
                yield Static("", id="status-display")

                # Connection info
                with Container(classes="info-section", id="connection-section"):
                    yield Static("[bold]Connection Info:[/]", classes="info-item")
                    yield Static("", id="ip-display", classes="info-item")
                    yield Static("", id="connect-display", classes="info-item")
                    yield Button("Copy Server Address", variant="default", id="copy-ip-btn")
                    yield Static("Port: 25565 (default)", classes="info-item")

                # Droplet details
                with Container(classes="info-section", id="droplet-section"):
                    yield Static("[bold]Droplet Details:[/]", classes="info-item")
                    yield Static("", id="size-display", classes="info-item")
                    yield Static("", id="region-display", classes="info-item")
                    yield Static("", id="vcpu-display", classes="info-item")
                    yield Static("", id="memory-display", classes="info-item")
                    yield Static("", id="disk-display", classes="info-item")

                # Control buttons
                yield Static("[bold]Server Controls:[/]", classes="info-item")
                with Horizontal(id="detail-buttons"):
                    yield Button("Power On", variant="success", id="poweron-btn")
                    yield Button("View Console", variant="success", id="console-btn")
                    yield Button("Power Off", variant="warning", id="poweroff-btn")
                    yield Button("Reboot", variant="default", id="reboot-btn")
                    yield Button("Delete Server", variant="error", id="delete-btn")
                    yield Button("Refresh Status", variant="default", id="refresh-detail-btn")
                    yield Button("Close", variant="primary", id="close-detail-btn")
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
        # Detail pane buttons
        elif event.button.id == "close-detail-btn":
            self.hide_detail_pane()
        elif event.button.id == "refresh-detail-btn":
            self.refresh_selected_server()
        elif event.button.id == "copy-ip-btn":
            self.copy_ip_address()
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

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the server table."""
        if event.row_key in self.droplet_map:
            droplet = self.droplet_map[event.row_key]
            self.show_detail_pane(droplet)

    def show_detail_pane(self, droplet: dict) -> None:
        """Show the detail pane with server information."""
        self.selected_droplet = droplet
        self.selected_droplet_id = droplet.get("id")
        self.selected_server_name = droplet.get("name", "Unknown")

        # Extract IP address
        self.selected_ip_address = "Pending..."
        for network in droplet.get("networks", {}).get("v4", []):
            if network.get("type") == "public":
                self.selected_ip_address = network.get("ip_address", "Pending...")
                break

        # Show the detail container
        detail_container = self.query_one("#detail-container", Container)
        detail_container.styles.display = "block"

        # Update all the fields
        self.update_detail_pane()

    def hide_detail_pane(self) -> None:
        """Hide the detail pane."""
        detail_container = self.query_one("#detail-container", Container)
        detail_container.styles.display = "none"
        self.selected_droplet = None
        self.selected_droplet_id = None
        self.selected_server_name = None
        self.selected_ip_address = None

    def update_detail_pane(self) -> None:
        """Update the detail pane with current server information."""
        if not self.selected_droplet:
            return

        droplet = self.selected_droplet

        # Update title
        self.query_one("#detail-title", Static).update(f"Server: {self.selected_server_name}")

        # Update status
        status = droplet.get("status", "unknown")
        status_color = "green" if status == "active" else "yellow" if status == "new" else "red"
        self.query_one("#status-display", Static).update(
            f"Status: [{status_color}]{status.upper()}[/]"
        )

        # Update connection info
        if self.selected_ip_address and self.selected_ip_address != "Pending...":
            self.query_one("#ip-display", Static).update(
                f"[bold reverse] {self.selected_ip_address} [/]"
            )
            self.query_one("#connect-display", Static).update(
                f"[dim]Connect with:[/] [bold]{self.selected_ip_address}:25565[/]"
            )
        else:
            self.query_one("#ip-display", Static).update(f"IP Address: {self.selected_ip_address}")
            self.query_one("#connect-display", Static).update("")

        # Update droplet details
        self.query_one("#size-display", Static).update(
            f"Size: {droplet.get('size', {}).get('slug', 'Unknown')}"
        )
        self.query_one("#region-display", Static).update(
            f"Region: {droplet.get('region', {}).get('slug', 'Unknown')}"
        )
        self.query_one("#vcpu-display", Static).update(f"vCPUs: {droplet.get('vcpus', 'Unknown')}")
        self.query_one("#memory-display", Static).update(
            f"Memory: {droplet.get('memory', 'Unknown')} MB"
        )
        self.query_one("#disk-display", Static).update(f"Disk: {droplet.get('disk', 'Unknown')} GB")

        # Update button visibility based on status
        status = droplet.get("status", "unknown")
        try:
            if status == "active":
                self.query_one("#poweron-btn", Button).display = False
                self.query_one("#console-btn", Button).display = True
                self.query_one("#poweroff-btn", Button).display = True
                self.query_one("#reboot-btn", Button).display = True
            else:
                self.query_one("#poweron-btn", Button).display = True
                self.query_one("#console-btn", Button).display = False
                self.query_one("#poweroff-btn", Button).display = False
                self.query_one("#reboot-btn", Button).display = False
        except Exception:
            pass  # Buttons might not be available yet

    def refresh_selected_server(self) -> None:
        """Refresh the selected server's information."""
        if self.selected_droplet_id:
            self.run_worker(self.fetch_selected_server_status(), exclusive=True)

    async def fetch_selected_server_status(self) -> None:
        """Fetch current status of the selected server."""
        if not self.selected_droplet_id:
            return

        try:
            from ..services.digitalocean import DigitalOceanService

            do_service = DigitalOceanService(self.app.settings)
            updated_droplet = await do_service.get_droplet(self.selected_droplet_id)

            # Update selected droplet data
            self.selected_droplet = updated_droplet

            # Update IP address
            self.selected_ip_address = "Pending..."
            for network in updated_droplet.get("networks", {}).get("v4", []):
                if network.get("type") == "public":
                    self.selected_ip_address = network.get("ip_address", "Pending...")
                    break

            # Update the display
            self.update_detail_pane()

            self.app.notify("Server status refreshed", severity="information")

        except Exception as e:
            self.app.notify(f"Error refreshing server: {e}", severity="error")

    def copy_ip_address(self) -> None:
        """Copy server IP address and port to clipboard."""
        if self.selected_ip_address and self.selected_ip_address != "Pending...":
            try:
                server_address = f"{self.selected_ip_address}:25565"
                pyperclip.copy(server_address)
                self.app.notify(
                    f"Server address {server_address} copied to clipboard", severity="information"
                )
            except Exception as e:
                self.app.notify(f"Failed to copy server address: {e}", severity="error")
        else:
            self.app.notify("No IP address available to copy", severity="warning")

    def open_console(self) -> None:
        """Open server console screen."""
        if not self.selected_droplet:
            return

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

        self.app.push_screen(ServerConsoleScreen(self.selected_droplet, ssh_private_key))

    async def power_on(self) -> None:
        """Power on the selected server."""
        if not self.selected_droplet_id:
            return

        try:
            from ..services.digitalocean import DigitalOceanService

            self.app.notify(f"Powering on {self.selected_server_name}...")
            do_service = DigitalOceanService(self.app.settings)
            await do_service.power_on(self.selected_droplet_id)
            self.app.notify(
                f"Power on command sent to {self.selected_server_name}", severity="information"
            )

            # Refresh after a delay
            import asyncio

            await asyncio.sleep(2)
            self.refresh_selected_server()

        except Exception as e:
            self.app.notify(f"Error powering on server: {e}", severity="error")

    async def power_off(self) -> None:
        """Power off the selected server."""
        if not self.selected_droplet_id:
            return

        try:
            from ..services.digitalocean import DigitalOceanService

            self.app.notify(f"Powering off {self.selected_server_name}...")
            do_service = DigitalOceanService(self.app.settings)
            await do_service.power_off(self.selected_droplet_id)
            self.app.notify(
                f"Power off command sent to {self.selected_server_name}", severity="warning"
            )

            # Refresh after a delay
            import asyncio

            await asyncio.sleep(2)
            self.refresh_selected_server()

        except Exception as e:
            self.app.notify(f"Error powering off server: {e}", severity="error")

    async def reboot(self) -> None:
        """Reboot the selected server."""
        if not self.selected_droplet_id:
            return

        try:
            from ..services.digitalocean import DigitalOceanService

            self.app.notify(f"Rebooting {self.selected_server_name}...")
            do_service = DigitalOceanService(self.app.settings)
            await do_service.reboot(self.selected_droplet_id)
            self.app.notify(
                f"Reboot command sent to {self.selected_server_name}", severity="information"
            )

            # Refresh after a delay
            import asyncio

            await asyncio.sleep(2)
            self.refresh_selected_server()

        except Exception as e:
            self.app.notify(f"Error rebooting server: {e}", severity="error")

    def confirm_delete(self) -> None:
        """Show confirmation dialog before deleting."""

        async def handle_delete_confirmation(confirmed: bool) -> None:
            """Handle the result of the delete confirmation."""
            if confirmed:
                await self.delete_server()

        self.app.push_screen(
            ConfirmDeleteModal(self.selected_server_name), handle_delete_confirmation
        )

    async def delete_server(self) -> None:
        """Delete the selected server."""
        if not self.selected_droplet_id:
            return

        try:
            from ..services.digitalocean import DigitalOceanService

            self.app.notify(f"Deleting {self.selected_server_name}...", severity="warning")
            do_service = DigitalOceanService(self.app.settings)
            await do_service.delete_droplet(self.selected_droplet_id)
            self.app.notify(f"Server {self.selected_server_name} deleted", severity="error")

            # Hide detail pane and refresh server list
            self.hide_detail_pane()
            self.run_worker(self.fetch_servers(), exclusive=False)

        except Exception as e:
            self.app.notify(f"Error deleting server: {e}", severity="error")
