"""Server creation progress screen."""

import asyncio

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from ..models.server import ServerConfig, ServerType
from ..services.digitalocean import DigitalOceanService
from ..services.minecraft.forge import ForgeInstaller
from ..services.minecraft.modpack import ModpackInstaller
from ..services.minecraft.vanilla import VanillaInstaller
from ..widgets.progress_log import ProgressLog


class ProgressScreen(Screen):
    """Screen showing server creation progress."""

    CSS = """
    ProgressScreen {
        align: center middle;
    }

    #progress-container {
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
        margin: 1 0;
        color: $text;
    }

    ProgressLog {
        height: 25;
        margin: 1 0;
    }

    Button {
        width: 100%;
        margin-top: 1;
    }
    """

    def __init__(self, server_config: ServerConfig):
        super().__init__()
        self.server_config = server_config
        self.droplet_id = None
        self.droplet_ip = None
        self.creation_complete = False
        self.creation_error = None

    def compose(self) -> ComposeResult:
        """Compose the progress screen."""
        yield Header()
        with Container(id="progress-container"):
            yield Static(f"Creating: {self.server_config.name}", id="title")
            yield Static("Initializing...", id="status")
            yield ProgressLog()
            yield Button("Back to Main Menu", variant="primary", id="done-btn", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        """Start server creation when mounted."""
        self.run_worker(self.create_server(), exclusive=True)

    async def create_server(self) -> None:
        """Create the server with progress updates."""
        log = self.query_one(ProgressLog)
        status = self.query_one("#status", Static)

        try:
            # 1. Initialize DigitalOcean service
            status.update("Connecting to DigitalOcean...")
            log.log_progress("Initializing DigitalOcean service...")

            do_service = DigitalOceanService(self.app.settings)

            # 2. Create droplet
            status.update("Creating droplet...")
            log.log_progress(f"Creating droplet: {self.server_config.name}")
            log.log_progress(f"Region: {self.app.settings.default_region}")
            log.log_progress(f"Size: {self.app.settings.default_size}")

            droplet = await do_service.create_droplet(
                name=self.server_config.name,
            )
            self.droplet_id = droplet["id"]
            log.log_progress(f"Droplet created with ID: {self.droplet_id}")

            # 3. Wait for droplet to become active
            status.update("Waiting for droplet to become active...")
            log.log_progress("Waiting for droplet to start (this may take 1-2 minutes)...")

            active_droplet = await do_service.wait_for_droplet_active(self.droplet_id)

            # Get IP address
            for network in active_droplet.get("networks", {}).get("v4", []):
                if network.get("type") == "public":
                    self.droplet_ip = network.get("ip_address")
                    break

            log.log_progress(f"Droplet is active! IP: {self.droplet_ip}")

            # 4. Wait for SSH to be ready
            status.update("Waiting for SSH to be ready...")
            log.log_progress("Waiting for SSH service to start (30 seconds)...")
            await asyncio.sleep(30)  # Give SSH time to start

            # 5. Install Minecraft
            status.update("Installing Minecraft server...")
            log.log_progress(f"Installing {self.server_config.server_type.value} server...")

            # Select installer based on type
            if self.server_config.server_type == ServerType.VANILLA:
                installer = VanillaInstaller(self.server_config)
            elif self.server_config.server_type == ServerType.FORGE:
                installer = ForgeInstaller(self.server_config)
            else:
                installer = ModpackInstaller(self.server_config)

            # Connect via SSH
            installer.connect_ssh(
                host=self.droplet_ip,
                username="root",
                key_path=str(self.app.settings.ssh_private_key_path),
            )

            # Run installation with progress callback
            def progress_callback(message: str):
                log.log_progress(message)

            await installer.install(progress_callback=progress_callback)

            installer.disconnect()

            # 6. Complete
            status.update("Server created successfully!")
            log.log_progress("")
            log.log_progress("=" * 60)
            log.log_progress("🎉 SERVER CREATED SUCCESSFULLY!")
            log.log_progress("=" * 60)
            log.log_progress(f"Server Name: {self.server_config.name}")
            log.log_progress(f"IP Address: {self.droplet_ip}")
            log.log_progress(f"Port: {self.server_config.server_port}")
            log.log_progress(f"Connect: {self.droplet_ip}:{self.server_config.server_port}")
            log.log_progress("")
            log.log_progress(
                "The server is starting up. It may take a few minutes before it's ready."
            )
            log.log_progress("You can now connect to your Minecraft server!")

            self.creation_complete = True

            # Enable the done button
            done_btn = self.query_one("#done-btn", Button)
            done_btn.disabled = False

        except Exception as e:
            status.update("Error creating server!")
            log.log_progress("")
            log.log_progress("=" * 60)
            log.log_progress(f"❌ ERROR: {e!s}")
            log.log_progress("=" * 60)
            log.log_progress("")
            log.log_progress(f"Server creation failed: {e}")

            if self.droplet_id:
                log.log_progress(f"Droplet ID {self.droplet_id} may still exist.")
                log.log_progress("You can delete it manually from the DigitalOcean dashboard.")

            self.creation_error = str(e)

            # Enable the done button
            done_btn = self.query_one("#done-btn", Button)
            done_btn.disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "done-btn":
            # Pop back to main menu
            self.app.pop_screen()
            self.app.pop_screen()  # Pop the create server screen too
