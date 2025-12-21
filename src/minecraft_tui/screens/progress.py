# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""Server creation progress screen."""

import asyncio
import threading

import pyperclip
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from ..models.server import ServerConfig, ServerType
from ..services.digitalocean import DigitalOceanService
from ..services.minecraft.fabric import FabricInstaller
from ..services.minecraft.forge import ForgeInstaller
from ..services.minecraft.modpack import ModpackInstaller
from ..services.minecraft.vanilla import VanillaInstaller
from ..utils.cloud_init import generate_cloud_init_config
from ..widgets.progress_log import ProgressLog


class ProgressScreen(Screen):
    """Screen showing server creation progress."""

    CSS = """
    ProgressScreen {
        height: 100%;
    }

    #progress-container {
        width: 100%;
        height: 1fr;
        border: solid $accent;
        padding: 2;
        background: $surface;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
        height: auto;
    }

    #status {
        text-align: center;
        margin: 1 0;
        color: $text;
        height: auto;
    }

    ProgressLog {
        height: 1fr;
        margin: 1 0;
    }

    Horizontal {
        height: auto;
    }

    Button {
        margin-top: 1;
    }
    """

    def __init__(self, server_config: ServerConfig, ssh_key_path: str):
        super().__init__()
        self.server_config = server_config
        self.ssh_key_path = ssh_key_path
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
            with Horizontal():
                yield Button("Back to Main Menu", variant="primary", id="done-btn", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        """Start server creation when mounted."""
        self.run_worker(self.create_server(), exclusive=True)

    def _thread_safe_log(self, message: str) -> None:
        """Thread-safe progress logging - detects thread and uses appropriate method."""
        if threading.current_thread() is threading.main_thread():
            # Already on main thread, call directly
            self._do_log(message)
        else:
            # On worker thread, use call_from_thread
            self.app.call_from_thread(self._do_log, message)

    def _do_log(self, message: str) -> None:
        """Actually write to the log (called on main thread)."""
        log = self.query_one(ProgressLog)
        log.log_progress(message)

    async def create_server(self) -> None:
        """Create the server with progress updates."""
        log = self.query_one(ProgressLog)
        status = self.query_one("#status", Static)

        try:
            # 1. Initialize DigitalOcean service
            status.update("Connecting to DigitalOcean...")
            log.log_progress("Initializing DigitalOcean service...")
            log.log_progress(f"Using SSH key: {self.ssh_key_path}")

            # Update settings to use user-provided SSH key
            from pathlib import Path

            from ..config import Settings

            settings = Settings()
            settings.digitalocean_token = self.app.settings.digitalocean_token
            settings.ssh_key_path = Path(self.ssh_key_path)

            # Derive private key path from public key path
            if self.ssh_key_path.endswith(".pub"):
                private_key_path = Path(self.ssh_key_path[:-4])
            else:
                private_key_path = Path(self.ssh_key_path)

            # Verify private key exists
            if not private_key_path.exists():
                raise FileNotFoundError(
                    f"Private key not found at {private_key_path}. "
                    f"Expected to find private key for public key: {self.ssh_key_path}"
                )

            settings.ssh_private_key_path = private_key_path

            do_service = DigitalOceanService(settings)
            log.log_progress("✓ SSH key verified/uploaded successfully")

            # 2. Create droplet with cloud-init security configuration
            status.update("Creating droplet...")
            log.log_progress(f"Creating droplet: {self.server_config.name}")

            # Use region and size from server config if available, otherwise use defaults
            region = getattr(self.server_config, "region", self.app.settings.default_region)
            droplet_size = getattr(
                self.server_config, "droplet_size", self.app.settings.default_size
            )

            log.log_progress(f"Region: {region}")
            log.log_progress(f"Size: {droplet_size}")
            log.log_progress("Configuring automatic security hardening (fail2ban, UFW)...")

            cloud_init = generate_cloud_init_config()

            # Determine modpack source for tagging
            modpack_source = None
            if self.server_config.modpack_file_path:
                # Use just the filename for the tag
                modpack_source = Path(self.server_config.modpack_file_path).name
            elif self.server_config.modpack_url:
                modpack_source = "url"

            # Determine loader version for tagging
            loader_version = None
            if self.server_config.server_type.value == "forge":
                loader_version = self.server_config.forge_version
            elif self.server_config.server_type.value == "fabric":
                loader_version = self.server_config.fabric_version
            elif self.server_config.modpack_loader:
                loader_version = self.server_config.modpack_loader_version

            droplet = await do_service.create_droplet(
                name=self.server_config.name,
                size=droplet_size,
                region=region,
                user_data=cloud_init,
                server_type=self.server_config.server_type.value,
                modpack_loader=self.server_config.modpack_loader,
                modpack_source=modpack_source,
                mc_version=self.server_config.minecraft_version,
                loader_version=loader_version,
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

            # 4. Wait for SSH to be ready and cloud-init to complete
            status.update("Waiting for SSH to be ready...")
            log.log_progress("Waiting for SSH service to start...")
            log.log_progress("Cloud-init is configuring security (fail2ban, firewall)...")
            log.log_progress("This may take 1-2 minutes...")
            await asyncio.sleep(60)  # Give SSH and cloud-init time to complete

            # 5. Install Minecraft
            status.update("Installing Minecraft server...")
            log.log_progress(f"Installing {self.server_config.server_type.value} server...")

            # Select installer based on type
            if self.server_config.server_type == ServerType.VANILLA:
                installer = VanillaInstaller(self.server_config)
            elif self.server_config.server_type == ServerType.FORGE:
                installer = ForgeInstaller(self.server_config)
            elif self.server_config.server_type == ServerType.FABRIC:
                installer = FabricInstaller(self.server_config)
            else:
                installer = ModpackInstaller(self.server_config)

            # Connect via SSH and install
            log.log_progress(f"Connecting via SSH using key: {settings.ssh_private_key_path}")

            # Use thread-safe callback for SSH operations (they run in asyncio.to_thread)
            await installer.connect_ssh(
                host=self.droplet_ip,
                username="root",
                key_path=str(settings.ssh_private_key_path),
                progress_callback=self._thread_safe_log,
            )

            # Initialize the installation log file on the server
            await installer.init_install_log(self._thread_safe_log)

            # Create a wrapped callback that queues messages for file logging
            wrapped_callback = installer.wrap_progress_callback(self._thread_safe_log)

            # Run installation with wrapped progress callback
            install_error = None
            try:
                await installer.install(progress_callback=wrapped_callback)
            except Exception as install_exc:
                install_error = install_exc
                raise
            finally:
                # Flush queued log messages to the file
                try:
                    await installer.flush_log_queue(progress_callback=self._thread_safe_log)
                    # Finalize the log with success/failure status
                    await installer.finalize_install_log(
                        success=(install_error is None),
                        error_message=str(install_error) if install_error else None,
                    )
                    log.log_progress(f"Installation log saved to: {installer.INSTALL_LOG_PATH}")
                except Exception as log_err:
                    log.log_progress(f"Warning: Could not save installation log: {log_err}")

            installer.disconnect()

            # 6. Complete
            status.update("Server created successfully!")
            log.log_progress("")
            log.log_progress("=" * 60)
            log.log_progress("🎉 SERVER CREATED SUCCESSFULLY!")
            log.log_progress("=" * 60)
            log.log_progress(f"Server Name: {self.server_config.name}")
            log.log_progress("")
            log.log_progress("📋 Copy this to connect:")
            log.log_progress(f"   {self.droplet_ip}:{self.server_config.server_port}")
            log.log_progress("")
            log.log_progress(f"IP Address: {self.droplet_ip}")
            log.log_progress(f"Port: {self.server_config.server_port}")
            log.log_progress("")
            log.log_progress(
                "The server is starting up. It may take a few minutes before it's ready."
            )
            log.log_progress("You can now connect to your Minecraft server!")

            # Automatically copy connection details to clipboard
            connection_string = f"{self.droplet_ip}:{self.server_config.server_port}"
            try:
                pyperclip.copy(connection_string)
                self.app.notify(
                    f"Connection details copied to clipboard: {connection_string}",
                    severity="information",
                )
            except Exception as e:
                # Don't fail if clipboard unavailable, just log it
                log.log_progress(f"Note: Could not copy to clipboard: {e}")

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
