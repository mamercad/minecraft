"""Server console screen with RCON support."""

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, RichLog, Static

from ..services.rcon_service import RconError, RconService


class ServerConsoleScreen(Screen):
    """Screen showing server console with RCON command support."""

    BINDINGS = [
        Binding("j", "focus_next", "Focus Next", show=False),
        Binding("k", "focus_previous", "Focus Previous", show=False),
        Binding("escape", "back", "Back", priority=True),
    ]

    CSS = """
    ServerConsoleScreen {
        height: 100%;
    }

    #console-container {
        width: 100%;
        height: 100%;
        border: solid $accent;
        padding: 1;
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
        margin-bottom: 1;
        color: $text-muted;
    }

    RichLog {
        height: 1fr;
        border: solid $primary;
        background: $panel;
        margin: 1 0;
    }

    #command-container {
        height: auto;
    }

    #command-input {
        width: 1fr;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, droplet: dict, ssh_key_path: str):
        super().__init__()
        self.droplet = droplet
        self.ssh_key_path = ssh_key_path
        self.server_name = droplet.get("name", "Unknown")

        # Get IP address
        self.ip_address = None
        for network in droplet.get("networks", {}).get("v4", []):
            if network.get("type") == "public":
                self.ip_address = network.get("ip_address")
                break

        self.rcon_service: RconService | None = None
        self.connected = False

    def compose(self) -> ComposeResult:
        """Compose the console screen."""
        yield Header()
        with Container(id="console-container"):
            yield Static(f"Server Console: {self.server_name}", id="title")
            yield Static("Connecting...", id="status")
            yield RichLog(id="console-log", highlight=True, markup=True)
            with Horizontal(id="command-container"):
                yield Input(
                    placeholder="Enter Minecraft command (e.g., 'list', 'say Hello')",
                    id="command-input",
                )
                yield Button("Send", variant="primary", id="send-btn")
                yield Button("Refresh Logs", variant="default", id="refresh-btn")
                yield Button("Back", variant="default", id="back-btn")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize console connection."""
        self.run_worker(self.connect_to_server(), exclusive=True)

    async def connect_to_server(self) -> None:
        """Connect to server RCON and load initial logs."""
        log = self.query_one(RichLog)
        status = self.query_one("#status", Static)

        if not self.ip_address:
            status.update("[red]Error: No IP address found[/]")
            log.write("[red]Cannot connect: Server has no IP address[/]")
            return

        try:
            # Initialize RCON service
            status.update("Initializing RCON connection...")
            log.write(f"[cyan]Connecting to {escape(self.ip_address)}...[/]")

            self.rcon_service = RconService(self.ip_address)

            # Get RCON password from server
            status.update("Retrieving RCON credentials...")
            log.write("[cyan]Retrieving RCON password from server...[/]")
            password = await self.rcon_service.get_rcon_password_from_server(self.ssh_key_path)
            log.write(f"[dim]Retrieved password (length: {len(password)} chars)[/]")
            log.write(f"[dim]Password: {escape(password)}[/]")
            log.write(f"[dim]Password bytes: {password.encode('utf-8').hex()}[/]")

            # Connect to RCON
            status.update("Connecting to RCON...")
            log.write("[cyan]Connecting to RCON...[/]")
            log.write(f"[dim]Connecting with password: {escape(password)}[/]")
            await self.rcon_service.connect(password)

            self.connected = True
            status.update(f"[green]Connected to {escape(self.ip_address)}:25575[/]")
            log.write("[green]✓ RCON connection established[/]")
            log.write("")

            # Load initial logs
            await self.load_logs()

        except RconError as e:
            error_str = str(e).lower()
            status.update(f"[red]RCON Error: {escape(str(e))}[/]")
            log.write(f"[red]✗ RCON connection failed: {escape(str(e))}[/]")
            log.write("")

            # Provide specific guidance based on error type
            if "did not respond to authentication" in error_str:
                log.write(
                    "[yellow bold]⚠ Server not responding to authentication - Likely password mismatch[/]"
                )
                log.write("")
                log.write(
                    "[cyan]This happens when the RCON password we sent doesn't match server.properties.[/]"
                )
                log.write(
                    "The server silently drops the connection instead of sending an error response."
                )
                log.write("")
                log.write("[yellow bold]Verify the password:[/]")
                log.write(
                    f"  [dim]ssh root@{self.ip_address} 'grep \"^rcon\\.password=\" /opt/minecraft/server.properties'[/]"
                )
                log.write("")
                log.write("[cyan bold]Common causes:[/]")
                log.write("  1. Server was created before RCON support was added")
                log.write("  2. server.properties was manually edited and password changed")
                log.write("  3. Password contains special characters not properly escaped")
                log.write("")
                log.write("[yellow bold]How to fix:[/]")
                log.write("  [yellow]Recommended: Recreate the server[/]")
                log.write("    Delete this server and create a new one with the latest version")
                log.write("")
                log.write("  [yellow]Or manually verify/fix:[/]")
                log.write(f"    ssh root@{self.ip_address}")
                log.write("    # Check current RCON settings:")
                log.write("    grep '^rcon\\.' /opt/minecraft/server.properties")
                log.write("    # Ensure rcon.address=0.0.0.0 exists")
                log.write("    # If you change settings, restart:")
                log.write("    systemctl restart minecraft")
            elif (
                "connection refused" in error_str
                or "errno 61" in error_str
                or "connect call failed" in error_str
            ):
                log.write(
                    "[yellow bold]⚠ Connection Refused - Nothing is listening on port 25575[/]"
                )
                log.write("")
                log.write("[cyan]Most likely causes:[/]")
                log.write("  1. Minecraft server is not running")
                log.write("  2. Minecraft server is still starting up (wait 60-90 seconds)")
                log.write("  3. Server was created before RCON fix (missing rcon.address=0.0.0.0)")
                log.write("")
                log.write("[yellow bold]Quick Diagnostics:[/]")
                log.write("")
                log.write("[yellow]• Check if Minecraft is running:[/]")
                log.write(
                    f"  [dim]ssh root@{self.ip_address} 'systemctl status minecraft | head -20'[/]"
                )
                log.write("")
                log.write("[yellow]• Check RCON configuration:[/]")
                log.write(
                    f"  [dim]ssh root@{self.ip_address} 'grep -E \"^(enable-rcon|rcon\\.)\" /opt/minecraft/server.properties'[/]"
                )
                log.write("  [green]Expected output:[/]")
                log.write("    enable-rcon=true")
                log.write("    rcon.address=0.0.0.0")
                log.write("    rcon.port=25575")
                log.write("    rcon.password=<password>")
                log.write("")
                log.write("[yellow]• Check what's listening on RCON port:[/]")
                log.write(
                    f"  [dim]ssh root@{self.ip_address} 'ss -tlnp | grep :25575 || echo \"Nothing listening on 25575\"'[/]"
                )
                log.write(
                    "  [green]Expected:[/] 0.0.0.0:25575 or *:25575 (bound to all interfaces)"
                )
                log.write("  [red]Problem:[/] 127.0.0.1:25575 (only localhost) or nothing at all")
                log.write("")
                log.write("[cyan bold]How to fix:[/]")
                log.write("  [yellow]If missing rcon.address:[/]")
                log.write(f"    ssh root@{self.ip_address}")
                log.write("    echo 'rcon.address=0.0.0.0' >> /opt/minecraft/server.properties")
                log.write("    systemctl restart minecraft")
                log.write("    # Wait 60-90 seconds, then try console again")
                log.write("")
                log.write("  [yellow]If server not running:[/]")
                log.write(f"    ssh root@{self.ip_address} 'systemctl start minecraft'")
                log.write("")
                log.write("  [yellow]Recommended: Recreate server with latest version[/]")
                log.write("    (Newer servers have rcon.address=0.0.0.0 by default)")
            elif "timeout" in error_str:
                log.write(
                    "[yellow bold]⚠ Connection Timeout - Server not responding on port 25575[/]"
                )
                log.write("")
                log.write("[cyan]Possible causes:[/]")
                log.write("  1. Firewall blocking port 25575")
                log.write("  2. Server IP address changed")
                log.write("  3. Droplet is powered off or unreachable")
                log.write("")
                log.write("[yellow bold]Quick Diagnostics:[/]")
                log.write("")
                log.write("[yellow]• Verify firewall allows RCON:[/]")
                log.write(f"  [dim]ssh root@{self.ip_address} 'ufw status | grep 25575'[/]")
                log.write("  [green]Expected:[/] 25575/tcp ALLOW Anywhere")
                log.write("")
                log.write("[yellow]• Check if server is reachable:[/]")
                log.write(f"  [dim]ping -c 3 {self.ip_address}[/]")
                log.write("")
                log.write("[yellow]• Test port connectivity:[/]")
                log.write(f"  [dim]nc -zv {self.ip_address} 25575[/]")
            else:
                # Generic troubleshooting for other errors
                log.write("[yellow bold]Troubleshooting Steps:[/]")
                log.write("")
                log.write("[yellow]1. Check server status:[/]")
                log.write(f"   [dim]ssh root@{self.ip_address} 'systemctl status minecraft'[/]")
                log.write("")
                log.write("[yellow]2. Verify RCON configuration:[/]")
                log.write(
                    f"   [dim]ssh root@{self.ip_address} 'grep -E \"^(enable-rcon|rcon\\.)\" /opt/minecraft/server.properties'[/]"
                )
                log.write("")
                log.write("[yellow]3. Check server logs:[/]")
                log.write(
                    f"   [dim]ssh root@{self.ip_address} 'tail -50 /opt/minecraft/logs/latest.log'[/]"
                )
        except Exception as e:
            status.update(f"[red]Error: {escape(str(e))}[/]")
            log.write(f"[red]✗ Connection failed: {escape(str(e))}[/]")

    async def load_logs(self) -> None:
        """Load server logs."""
        log = self.query_one(RichLog)

        if not self.rcon_service:
            log.write("[red]Not connected to server[/]")
            return

        try:
            log.write("[cyan]Loading server logs...[/]")
            logs = await self.rcon_service.get_server_logs(self.ssh_key_path, lines=50)

            log.write("[dim]--- Recent Server Logs ---[/]")
            for line in logs:
                if line.strip():
                    log.write(escape(line))
            log.write("[dim]--- End of Logs ---[/]")
            log.write("")

        except RconError as e:
            log.write(f"[red]Failed to load logs: {escape(str(e))}[/]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "back-btn":
            self.action_back()
        elif event.button.id == "send-btn":
            self.send_command()
        elif event.button.id == "refresh-btn":
            self.run_worker(self.load_logs())

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command input submission."""
        if event.input.id == "command-input":
            self.send_command()

    def send_command(self) -> None:
        """Send command to server."""
        command_input = self.query_one("#command-input", Input)
        command = command_input.value.strip()

        if not command:
            return

        # Clear input
        command_input.value = ""

        # Execute command
        self.run_worker(self.execute_command(command))

    async def execute_command(self, command: str) -> None:
        """Execute RCON command.

        Args:
            command: Minecraft command to execute
        """
        log = self.query_one(RichLog)

        if not self.connected or not self.rcon_service:
            log.write("[red]Not connected to server[/]")
            return

        try:
            log.write(f"[cyan]> {escape(command)}[/]")
            response = await self.rcon_service.send_command(command)

            # Display response
            if response:
                for line in response.split("\n"):
                    if line.strip():
                        log.write(f"[green]{escape(line)}[/]")
            else:
                log.write("[dim]Command executed (no response)[/]")

        except RconError as e:
            log.write(f"[red]Command failed: {escape(str(e))}[/]")
        except Exception as e:
            log.write(f"[red]Error: {escape(str(e))}[/]")

    def action_back(self) -> None:
        """Go back to previous screen."""
        if self.rcon_service:
            self.rcon_service.disconnect()
        self.app.pop_screen()
