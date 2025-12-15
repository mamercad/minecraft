"""Server console screen with RCON support."""

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
            log.write(f"[cyan]Connecting to {self.ip_address}...[/]")

            self.rcon_service = RconService(self.ip_address)

            # Get RCON password from server
            status.update("Retrieving RCON credentials...")
            log.write("[cyan]Retrieving RCON password from server...[/]")
            password = await self.rcon_service.get_rcon_password_from_server(
                self.ssh_key_path
            )

            # Connect to RCON
            status.update("Connecting to RCON...")
            log.write("[cyan]Connecting to RCON...[/]")
            await self.rcon_service.connect(password)

            self.connected = True
            status.update(f"[green]Connected to {self.ip_address}:25575[/]")
            log.write("[green]✓ RCON connection established[/]")
            log.write("")

            # Load initial logs
            await self.load_logs()

        except RconError as e:
            status.update(f"[red]RCON Error: {e}[/]")
            log.write(f"[red]✗ RCON connection failed: {e}[/]")
            log.write("")
            log.write("[yellow]Tip: Make sure the server is running and RCON is enabled[/]")
        except Exception as e:
            status.update(f"[red]Error: {e}[/]")
            log.write(f"[red]✗ Connection failed: {e}[/]")

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
                    log.write(line)
            log.write("[dim]--- End of Logs ---[/]")
            log.write("")

        except RconError as e:
            log.write(f"[red]Failed to load logs: {e}[/]")

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
            log.write(f"[cyan]> {command}[/]")
            response = await self.rcon_service.send_command(command)

            # Display response
            if response:
                for line in response.split("\n"):
                    if line.strip():
                        log.write(f"[green]{line}[/]")
            else:
                log.write("[dim]Command executed (no response)[/]")

        except RconError as e:
            log.write(f"[red]Command failed: {e}[/]")
        except Exception as e:
            log.write(f"[red]Error: {e}[/]")

    def action_back(self) -> None:
        """Go back to previous screen."""
        if self.rcon_service:
            self.rcon_service.disconnect()
        self.app.pop_screen()
