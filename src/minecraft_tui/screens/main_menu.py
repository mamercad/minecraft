# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""Main menu screen."""

import asyncio
import contextlib
from pathlib import Path

import paramiko
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

    #droplet-id {
        text-align: center;
        margin-bottom: 1;
        color: $text-muted;
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

    def __init__(self, server_name: str, droplet_id: int | None = None):
        super().__init__()
        self.server_name = server_name
        self.droplet_id = droplet_id

    def compose(self) -> ComposeResult:
        """Compose the confirmation dialog."""
        with Container(id="dialog"):
            yield Label(
                f"Are you sure you want to delete server '{self.server_name}'?",
                id="question",
            )
            if self.droplet_id:
                yield Label(
                    f"Droplet ID: {self.droplet_id}",
                    id="droplet-id",
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
        self._fetching_servers = False  # Prevent duplicate fetches

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
        max-height: 12;
        border: solid $accent;
        padding: 1;
        background: $surface;
        margin-bottom: 1;
    }

    #creeper-art {
        width: auto;
        height: auto;
        max-height: 10;
        color: $success;
        text-style: bold;
        padding: 0 1;
        margin-right: 1;
    }

    #menu-section {
        width: 1fr;
        height: auto;
        max-height: 10;
        padding: 0 1;
    }

    #title {
        text-style: bold;
        color: $accent;
        margin-bottom: 0;
    }

    #account-info {
        color: $text-muted;
        margin-bottom: 1;
        padding: 0;
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
        # Minecraft Creeper ASCII art (compact)
        creeper = """████████████
██        ██
██ ██  ██ ██
██        ██
██ ██████ ██
██ █    █ ██
████████████"""

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
                    yield Button("Start Game", variant="success", id="startgame-btn")
                    yield Button("View Console", variant="success", id="console-btn")
                    yield Button("SSH Shell", variant="success", id="ssh-btn")
                    yield Button("Stop Game", variant="warning", id="stopgame-btn")
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
        table.add_columns("ID", "Name", "Type", "MC", "Loader", "IP", "Size", "Region", "Status", "Game")
        # Fetch account info and servers
        self.run_worker(self.fetch_account_info(), exclusive=True, group="account")
        self.run_worker(self.fetch_servers(), exclusive=True, group="servers")

    def on_screen_resume(self) -> None:
        """Called when returning to this screen."""
        # Refresh the server list when returning from another screen
        # Use call_after_refresh to ensure UI is ready
        self.call_after_refresh(self._refresh_servers)

    def _refresh_servers(self) -> None:
        """Refresh the server list."""
        self.run_worker(self.fetch_servers(), exclusive=True, group="servers")

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
        # Prevent duplicate fetches
        if self._fetching_servers:
            return
        self._fetching_servers = True

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
                table.add_row("-", "No servers found", "-", "-", "-", "-", "-", "-", "-", "-none-")
                return

            status.update(f"Found {len(droplets)} server(s)")

            # Add each droplet to the table
            for droplet in droplets:
                droplet_id = str(droplet.get("id", "?"))
                name = droplet.get("name", "Unknown")

                # Get server type and versions from tags
                tags = droplet.get("tags", [])
                server_type = "unknown"
                modpack_loader = None
                mc_version = None
                loader_version = None
                type_tags = {"vanilla", "forge", "fabric", "modpack"}

                for tag in tags:
                    tag_lower = tag.lower()
                    if tag_lower in type_tags:
                        server_type = tag_lower
                    elif tag_lower.startswith("loader-"):
                        modpack_loader = tag_lower[7:]  # Remove "loader-" prefix
                    elif tag_lower.startswith("mc-"):
                        mc_version = tag[3:]  # Remove "mc-" prefix (preserve case)
                    elif tag_lower.startswith("lv-"):
                        loader_version = tag[3:]  # Remove "lv-" prefix

                # Format type display (simplified)
                if server_type == "modpack" and modpack_loader:
                    type_display = f"modpack/{modpack_loader}"
                else:
                    type_display = server_type

                # Format MC version and loader version for display
                mc_display = mc_version or "-"
                loader_display = loader_version or "-"

                # Get IP address
                ip_address = "Pending..."
                for network in droplet.get("networks", {}).get("v4", []):
                    if network.get("type") == "public":
                        ip_address = network.get("ip_address", "Pending...")
                        break

                size_obj = droplet.get("size", {})
                size = size_obj.get("slug", "Unknown")
                region = droplet.get("region", {}).get("slug", "Unknown")
                status_text = droplet.get("status", "unknown")

                # Add row and store droplet data (game status starts with placeholder)
                # Use wide placeholder to set proper column width for "✓ running"
                row_key = table.add_row(
                    droplet_id,
                    name,
                    type_display,
                    mc_display,
                    loader_display,
                    ip_address,
                    size,
                    region,
                    status_text,
                    "checking..",
                )
                self.droplet_map[row_key] = droplet

            # Start background game status checks for active droplets
            # Use exclusive=False so it doesn't get cancelled
            self.run_worker(self.check_game_statuses(), exclusive=False, group="game-status")

        except Exception as e:
            status.update(f"Error loading servers: {e}")
            table.clear()
            table.add_row("-", "Error", "-", "-", "-", str(e)[:20], "-", "-", "-", "-error-")
        finally:
            self._fetching_servers = False

    async def check_game_statuses(self) -> None:
        """Check game server status for all active droplets via SSH."""
        try:
            table = self.query_one(DataTable)
        except Exception:
            return  # Table not ready

        if not self.droplet_map:
            return  # No servers to check

        # Get the Game column key (it's the 10th column, index 9)
        game_col_idx = 9

        # Debug: show we're starting the check
        status = self.query_one("#server-status", Static)
        status.update(f"Checking game status for {len(self.droplet_map)} server(s)...")

        # Find SSH key
        ssh_private_key = None
        default_key = self.app.settings.ssh_private_key_path
        if default_key and Path(default_key).exists():
            ssh_private_key = str(default_key)
        else:
            ssh_dir = Path.home() / ".ssh"
            if ssh_dir.exists():
                for pub_key in sorted(ssh_dir.glob("*.pub")):
                    private_key = pub_key.parent / pub_key.stem
                    if private_key.exists():
                        ssh_private_key = str(private_key)
                        break

        if not ssh_private_key:
            # Update all to show "no key" indicator
            for row_key in self.droplet_map:
                with contextlib.suppress(Exception):
                    table.update_cell_at((table.get_row_index(row_key), game_col_idx), "no key")
            return

        # Check each active droplet
        for row_key, droplet in list(self.droplet_map.items()):
            try:
                row_idx = table.get_row_index(row_key)
            except Exception:
                continue

            if droplet.get("status") != "active":
                # Update non-active droplets to show "-"
                with contextlib.suppress(Exception):
                    table.update_cell_at((row_idx, game_col_idx), "-")
                continue

            # Get IP address
            ip_address = None
            for network in droplet.get("networks", {}).get("v4", []):
                if network.get("type") == "public":
                    ip_address = network.get("ip_address")
                    break

            if not ip_address:
                with contextlib.suppress(Exception):
                    table.update_cell_at((row_idx, game_col_idx), "no ip")
                continue

            # Check game status via SSH
            game_status = await self._check_single_game_status(ip_address, ssh_private_key)
            with contextlib.suppress(Exception):
                table.update_cell_at((row_idx, game_col_idx), game_status)

        # Update status when done
        with contextlib.suppress(Exception):
            status.update(f"Found {len(self.droplet_map)} server(s)")

    async def _check_single_game_status(self, ip: str, key_path: str) -> str:
        """Check if Minecraft server is running on a single host."""
        try:

            def _ssh_check():
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                try:
                    client.connect(
                        hostname=ip,
                        username="root",
                        key_filename=key_path,
                        timeout=10,
                        banner_timeout=10,
                        auth_timeout=10,
                    )
                    # Check systemd service status
                    stdin, stdout, stderr = client.exec_command(
                        "systemctl is-active minecraft 2>/dev/null || "
                        "systemctl is-active minecraft-server 2>/dev/null || "
                        "echo 'unknown'"
                    )
                    result = stdout.read().decode().strip()
                    return result
                finally:
                    client.close()

            result = await asyncio.to_thread(_ssh_check)

            status_map = {
                "active": "✓ running",
                "inactive": "stopped",
                "failed": "✗ failed",
                "unknown": "? unknown",
            }
            return status_map.get(result, f"? {result[:10]}")

        except TimeoutError:
            return "timeout"
        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str:
                return "timeout"
            elif "refused" in error_str:
                return "refused"
            elif "authentication" in error_str or "auth" in error_str:
                return "auth err"
            return "ssh err"

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
        elif event.button.id == "ssh-btn":
            self.open_ssh_shell()
        elif event.button.id == "poweron-btn":
            self.run_worker(self.power_on())
        elif event.button.id == "poweroff-btn":
            self.run_worker(self.power_off())
        elif event.button.id == "reboot-btn":
            self.run_worker(self.reboot())
        elif event.button.id == "startgame-btn":
            self.run_worker(self.start_game())
        elif event.button.id == "stopgame-btn":
            self.run_worker(self.stop_game())
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
                self.query_one("#startgame-btn", Button).display = True
                self.query_one("#console-btn", Button).display = True
                self.query_one("#ssh-btn", Button).display = True
                self.query_one("#stopgame-btn", Button).display = True
                self.query_one("#poweroff-btn", Button).display = True
                self.query_one("#reboot-btn", Button).display = True
            else:
                self.query_one("#poweron-btn", Button).display = True
                self.query_one("#startgame-btn", Button).display = False
                self.query_one("#console-btn", Button).display = False
                self.query_one("#ssh-btn", Button).display = False
                self.query_one("#stopgame-btn", Button).display = False
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

    def open_ssh_shell(self) -> None:
        """Open an interactive SSH shell to the server."""
        import subprocess

        if not self.selected_droplet:
            return

        if not self.selected_ip_address or self.selected_ip_address == "Pending...":
            self.app.notify("Server IP not available yet", severity="warning")
            return

        # Find SSH key
        ssh_private_key = self._get_ssh_key()
        if not ssh_private_key:
            self.app.notify(
                "No valid SSH key found. Please configure SSH_PRIVATE_KEY_PATH in settings.",
                severity="error",
            )
            return

        # Build SSH command
        ssh_cmd = [
            "ssh",
            "-i", ssh_private_key,
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"root@{self.selected_ip_address}",
        ]

        # Use Textual's suspend to temporarily give control to the terminal
        with self.app.suspend():
            try:
                # Print a helpful message
                print(f"\n{'=' * 60}")
                print(f"Connecting to {self.selected_server_name} ({self.selected_ip_address})...")
                print(f"{'=' * 60}")
                print("Type 'exit' or press Ctrl+D to return to the TUI.\n")

                # Run SSH interactively
                subprocess.run(ssh_cmd)

                print(f"\n{'=' * 60}")
                print("SSH session ended. Returning to TUI...")
                print(f"{'=' * 60}\n")
            except Exception as e:
                print(f"\nSSH failed: {e}\n")

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

    async def start_game(self) -> None:
        """Start the Minecraft game service on the server."""
        if not self.selected_ip_address or self.selected_ip_address == "Pending...":
            self.app.notify("Server IP not available", severity="error")
            return

        try:
            self.app.notify(f"Starting Minecraft on {self.selected_server_name}...")

            # Find SSH key
            ssh_private_key = self._get_ssh_key()
            if not ssh_private_key:
                self.app.notify("No SSH key found", severity="error")
                return

            # Run systemctl start via SSH
            result = await self._run_ssh_command(
                self.selected_ip_address, ssh_private_key, "systemctl start minecraft"
            )

            if result:
                self.app.notify(
                    f"Minecraft started on {self.selected_server_name}", severity="information"
                )
            else:
                self.app.notify(
                    f"Start command sent to {self.selected_server_name}", severity="information"
                )

            # Refresh game status
            self.run_worker(self.check_game_statuses(), exclusive=False, group="game-status")

        except Exception as e:
            self.app.notify(f"Error starting game: {e}", severity="error")

    async def stop_game(self) -> None:
        """Stop the Minecraft game service on the server."""
        if not self.selected_ip_address or self.selected_ip_address == "Pending...":
            self.app.notify("Server IP not available", severity="error")
            return

        try:
            self.app.notify(f"Stopping Minecraft on {self.selected_server_name}...")

            # Find SSH key
            ssh_private_key = self._get_ssh_key()
            if not ssh_private_key:
                self.app.notify("No SSH key found", severity="error")
                return

            # Run systemctl stop via SSH
            result = await self._run_ssh_command(
                self.selected_ip_address, ssh_private_key, "systemctl stop minecraft"
            )

            if result:
                self.app.notify(
                    f"Minecraft stopped on {self.selected_server_name}", severity="warning"
                )
            else:
                self.app.notify(
                    f"Stop command sent to {self.selected_server_name}", severity="warning"
                )

            # Refresh game status
            self.run_worker(self.check_game_statuses(), exclusive=False, group="game-status")

        except Exception as e:
            self.app.notify(f"Error stopping game: {e}", severity="error")

    def _get_ssh_key(self) -> str | None:
        """Find a valid SSH private key."""
        default_key = self.app.settings.ssh_private_key_path
        if default_key and Path(default_key).exists():
            return str(default_key)

        ssh_dir = Path.home() / ".ssh"
        if ssh_dir.exists():
            for pub_key in sorted(ssh_dir.glob("*.pub")):
                private_key = pub_key.parent / pub_key.stem
                if private_key.exists():
                    return str(private_key)
        return None

    async def _run_ssh_command(self, ip: str, key_path: str, command: str) -> bool:
        """Run a command on the server via SSH."""

        def _ssh_exec():
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(
                    hostname=ip,
                    username="root",
                    key_filename=key_path,
                    timeout=10,
                )
                stdin, stdout, stderr = client.exec_command(command)
                exit_status = stdout.channel.recv_exit_status()
                return exit_status == 0
            finally:
                client.close()

        return await asyncio.to_thread(_ssh_exec)

    def confirm_delete(self) -> None:
        """Show confirmation dialog before deleting."""

        async def handle_delete_confirmation(confirmed: bool) -> None:
            """Handle the result of the delete confirmation."""
            if confirmed:
                await self.delete_server()

        self.app.push_screen(
            ConfirmDeleteModal(self.selected_server_name, self.selected_droplet_id),
            handle_delete_confirmation,
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
