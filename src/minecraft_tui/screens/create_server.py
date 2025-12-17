"""Server creation wizard screen."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    RadioButton,
    Select,
    Static,
    TextArea,
)

from ..models.server import ServerType
from ..widgets import ViRadioSet


class CreateServerScreen(Screen):
    """Multi-step server creation wizard."""

    BINDINGS = [
        # Vi-style navigation
        Binding("j", "focus_next", "Focus Next", show=False),
        Binding("k", "focus_previous", "Focus Previous", show=False),
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    CSS = """
    CreateServerScreen {
        height: 100%;
    }

    #wizard-container {
        width: 100%;
        height: 100%;
        border: solid $accent;
        padding: 2;
        background: $surface;
    }

    #step-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 2;
    }

    #step-content {
        height: 1fr;
        padding: 1;
        overflow-y: auto;
    }

    #nav-buttons {
        height: auto;
        margin-top: 2;
    }

    Button {
        margin: 0 1;
    }

    RadioSet {
        margin: 1 0;
    }

    Input {
        margin: 1 0;
    }

    Label {
        margin: 1 0;
    }

    TextArea {
        height: 1fr;
        margin: 1 0;
    }
    """

    def __init__(self):
        super().__init__()
        self.current_step = 1
        self.max_steps = 5

        # Detect default SSH key
        from ..utils.name_generator import generate_server_name
        from ..utils.ssh_helper import get_default_ssh_key_path

        default_ssh_key = get_default_ssh_key_path()
        default_name = generate_server_name()

        self.server_data = {
            "server_type": ServerType.VANILLA,  # Default to vanilla
            "minecraft_version": "1.20.1",
            "forge_version": None,
            "fabric_version": None,
            "modpack_url": None,
            "name": default_name,  # Auto-generated name
            "max_players": 20,
            "memory_mb": 3072,
            "accept_eula": False,
            "ssh_key_path": default_ssh_key,
        }

    def compose(self) -> ComposeResult:
        """Compose the wizard."""
        yield Header()
        with Container(id="wizard-container"):
            yield Static(
                f"Create New Server - Step {self.current_step}/{self.max_steps}", id="step-title"
            )
            yield Container(id="step-content")
            with Horizontal(id="nav-buttons"):
                yield Button("Back", id="back-btn", variant="default")
                yield Button("Next", id="next-btn", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize first step."""
        self.update_step()

    def update_step(self):
        """Update the displayed step."""
        # Update title
        title = self.query_one("#step-title", Static)
        title.update(f"Create New Server - Step {self.current_step}/{self.max_steps}")

        # Update content
        content_container = self.query_one("#step-content", Container)
        content_container.remove_children()

        if self.current_step == 1:
            self.show_step_1(content_container)
        elif self.current_step == 2:
            self.show_step_2(content_container)
        elif self.current_step == 3:
            self.show_step_3(content_container)
        elif self.current_step == 4:
            self.show_step_4(content_container)
        elif self.current_step == 5:
            self.show_step_5(content_container)

        # Update button visibility
        back_btn = self.query_one("#back-btn", Button)
        next_btn = self.query_one("#next-btn", Button)

        # Change Back to Cancel on first step
        if self.current_step == 1:
            back_btn.label = "Cancel"
            back_btn.variant = "error"
        else:
            back_btn.label = "Back"
            back_btn.variant = "default"

        back_btn.disabled = False  # Always enabled
        next_btn.label = "Create Server" if self.current_step == self.max_steps else "Next"

        # Auto-focus Next button on step 1
        if self.current_step == 1:
            next_btn.focus()

    def show_step_1(self, container: Container):
        """Step 1: Select server type."""
        container.mount(Label("Select Server Type:"))
        radio_set = ViRadioSet(id="server-type")
        container.mount(radio_set)
        radio_set.mount(RadioButton("Vanilla Minecraft", id="vanilla", value=True))  # Default
        radio_set.mount(RadioButton("Forge (Modded)", id="forge"))
        radio_set.mount(RadioButton("Fabric (Modded)", id="fabric"))
        radio_set.mount(RadioButton("Custom Modpack", id="modpack"))

    def show_step_2(self, container: Container):
        """Step 2: Version selection."""
        container.mount(Label("Server Configuration:"))
        container.mount(Label("Minecraft Version:"))
        container.mount(Static("Loading versions from Mojang...", id="version-status"))

        # Launch async worker to load versions
        self.run_worker(self._load_versions(container), exclusive=False)

        if self.server_data["server_type"] == ServerType.FORGE:
            container.mount(Label("Forge Version:"))
            container.mount(
                Input(
                    value=self.server_data.get("forge_version", ""),
                    placeholder="e.g., 47.2.0 (or leave empty for latest)",
                    id="forge-version",
                )
            )
        elif self.server_data["server_type"] == ServerType.FABRIC:
            container.mount(Label("Fabric Loader Version:"))
            container.mount(
                Input(
                    value=self.server_data.get("fabric_version", ""),
                    placeholder="e.g., 0.16.0 (or leave empty for latest)",
                    id="fabric-version",
                )
            )
        elif self.server_data["server_type"] == ServerType.MODPACK:
            container.mount(Label("Modpack URL:"))
            container.mount(
                Input(
                    value=self.server_data.get("modpack_url", ""),
                    placeholder="https://example.com/modpack.zip",
                    id="modpack-url",
                )
            )

    def show_step_3(self, container: Container):
        """Step 3: Server configuration."""
        container.mount(Label("Server Settings:"))
        container.mount(Label("Server Name:"))
        container.mount(
            Input(
                value=self.server_data.get("name", ""),
                placeholder="My Minecraft Server",
                id="server-name",
            )
        )

        container.mount(Label("Max Players:"))
        container.mount(
            Input(value=str(self.server_data["max_players"]), placeholder="20", id="max-players")
        )

        # Droplet size selection
        from ..config import Settings

        settings = Settings()
        default_size = settings.default_size
        current_size = self.server_data.get("droplet_size", default_size)

        container.mount(Label("Droplet Size:"))
        size_radio_set = ViRadioSet(id="droplet-size-selector")
        container.mount(size_radio_set)

        # Common droplet sizes for Minecraft servers
        sizes = [
            ("s-1vcpu-2gb", "Basic (1 vCPU, 2GB RAM) - Small servers"),
            ("s-2vcpu-2gb", "Standard (2 vCPU, 2GB RAM) - Light servers"),
            ("s-2vcpu-4gb", "Recommended (2 vCPU, 4GB RAM) - Most servers"),
            ("s-4vcpu-8gb", "Performance (4 vCPU, 8GB RAM) - Modded/Large servers"),
            ("s-8vcpu-16gb", "Premium (8 vCPU, 16GB RAM) - Very large/heavy modpacks"),
        ]

        for slug, description in sizes:
            size_radio_set.mount(
                RadioButton(
                    description,
                    id=f"size-{slug}",
                    value=(slug == current_size),
                )
            )

        # Region selection
        default_region = settings.default_region
        current_region = self.server_data.get("region", default_region)

        container.mount(Label("Region:"))
        region_radio_set = ViRadioSet(id="region-selector")
        container.mount(region_radio_set)

        # Common DigitalOcean regions
        regions = [
            ("nyc1", "New York 1 (US East)"),
            ("nyc3", "New York 3 (US East)"),
            ("sfo3", "San Francisco 3 (US West)"),
            ("ams3", "Amsterdam 3 (Europe)"),
            ("sgp1", "Singapore 1 (Asia Pacific)"),
            ("lon1", "London 1 (Europe)"),
            ("fra1", "Frankfurt 1 (Europe)"),
            ("tor1", "Toronto 1 (Canada)"),
            ("blr1", "Bangalore 1 (Asia Pacific)"),
        ]

        for slug, description in regions:
            region_radio_set.mount(
                RadioButton(
                    description,
                    id=f"region-{slug}",
                    value=(slug == current_region),
                )
            )

        # Find SSH public keys in ~/.ssh that have matching private keys
        from pathlib import Path

        ssh_dir = Path.home() / ".ssh"
        ssh_keys = []
        if ssh_dir.exists():
            # Only include public keys that have corresponding private keys
            for pub_key in sorted(ssh_dir.glob("*.pub")):
                # Check if private key exists (same name without .pub)
                private_key = pub_key.parent / pub_key.stem
                if private_key.exists():
                    ssh_keys.append(pub_key)

        container.mount(Label("SSH Public Key:"))
        if ssh_keys:
            # Show available keys
            radio_set = ViRadioSet(id="ssh-key-selector")
            container.mount(radio_set)
            for i, key_path in enumerate(ssh_keys):
                is_default = str(key_path) == self.server_data.get("ssh_key_path", "")
                radio_set.mount(
                    RadioButton(
                        f"{key_path.name} ({key_path})",
                        id=f"ssh-key-{i}",
                        value=is_default or (i == 0 and not self.server_data.get("ssh_key_path")),
                    )
                )
            # Add custom option
            radio_set.mount(RadioButton("Custom path", id="ssh-key-custom"))

            # Show custom path input (hidden by default)
            container.mount(Label("Custom SSH Key Path:", classes="custom-ssh-label"))
            container.mount(
                Input(
                    value="" if ssh_keys else self.server_data.get("ssh_key_path", ""),
                    placeholder="Enter full path to .pub file",
                    id="ssh-key-custom-path",
                    classes="custom-ssh-input",
                )
            )
        else:
            # No keys found, just show input
            container.mount(Static("[yellow]No SSH keys found in ~/.ssh/[/]"))
            container.mount(
                Input(
                    value=self.server_data.get("ssh_key_path", ""),
                    placeholder="Enter full path to .pub file",
                    id="ssh-key-path",
                )
            )

        container.mount(Checkbox("I accept the Minecraft EULA", id="eula-checkbox"))

    def show_step_4(self, container: Container):
        """Step 4: Edit server.properties."""
        container.mount(Label("Server Properties Configuration:"))
        container.mount(
            Static(
                "Edit the server.properties below. "
                "These settings control your Minecraft server behavior."
            )
        )

        # Generate default server.properties if not already set
        if "server_properties_text" not in self.server_data:
            self.server_data["server_properties_text"] = self.generate_default_properties()

        text_area = TextArea(
            self.server_data["server_properties_text"],
            language="properties",
            theme="monokai",
            id="properties-editor",
        )
        container.mount(text_area)
        container.mount(
            Static(
                "[dim]Common properties: gamemode, difficulty, pvp, "
                "spawn-protection, view-distance, etc.[/]"
            )
        )

    def show_step_5(self, container: Container):
        """Step 5: Review and confirm."""
        container.mount(Label("Review Server Configuration:"))
        container.mount(Static(f"Server Type: {self.server_data['server_type']}"))
        container.mount(Static(f"Minecraft Version: {self.server_data['minecraft_version']}"))
        if self.server_data.get("forge_version"):
            container.mount(Static(f"Forge Version: {self.server_data['forge_version']}"))
        if self.server_data.get("fabric_version"):
            container.mount(Static(f"Fabric Loader Version: {self.server_data['fabric_version']}"))
        if self.server_data.get("modpack_url"):
            container.mount(Static(f"Modpack URL: {self.server_data['modpack_url']}"))
        container.mount(Static(f"Server Name: {self.server_data['name']}"))
        container.mount(Static(f"Max Players: {self.server_data['max_players']}"))
        container.mount(Static(f"Region: {self.server_data.get('region', 'nyc3')}"))
        container.mount(
            Static(f"Droplet Size: {self.server_data.get('droplet_size', 's-2vcpu-4gb')}")
        )
        container.mount(Static(f"SSH Key: {self.server_data['ssh_key_path']}"))
        container.mount(Static(f"EULA Accepted: {self.server_data['accept_eula']}"))

        # Show finalized server.properties
        container.mount(Label("\nFinalized Server Properties:"))
        properties_text = self.server_data.get("server_properties_text", "")
        text_area = TextArea(
            properties_text,
            language="properties",
            theme="monokai",
            read_only=True,
            id="properties-review",
        )
        container.mount(text_area)
        container.mount(Static("[dim]These properties will be deployed to your server[/]"))

    async def _load_versions(self, container: Container):
        """Async worker to load Minecraft versions and mount Select widget."""
        try:
            from ..services.minecraft.version_service import MinecraftVersionService

            service = MinecraftVersionService()
            versions = await service.fetch_versions(limit=20)
            latest = await service.get_latest_release()

            # Remove loading indicator
            try:
                loading = container.query_one("#version-status", Static)
                loading.remove()
            except Exception:
                pass

            # Mount Select widget with versions
            options = [(v.version, v.version) for v in versions]
            select = Select(
                options=options,
                value=latest,
                id="mc-version-select",
            )
            container.mount(select)

        except Exception:
            # Handle error - show fallback Input
            try:
                loading = container.query_one("#version-status", Static)
                loading.update("[yellow]Could not load versions from Mojang[/]")
            except Exception:
                pass

            # Mount Input as fallback
            container.mount(
                Input(
                    value=self.server_data["minecraft_version"],
                    placeholder="e.g., 1.21.11",
                    id="mc-version-input",
                )
            )

    def generate_default_properties(self) -> str:
        """Generate default server.properties content."""
        import secrets

        max_players = self.server_data.get("max_players", 20)
        # Generate a secure RCON password
        rcon_password = secrets.token_urlsafe(16)
        self.server_data["rcon_password"] = rcon_password

        properties = f"""# Minecraft Server Properties
# Edit these settings to customize your server

# Server identity
motd=A Minecraft Server
server-port=25565
max-players={max_players}

# Gameplay
gamemode=survival
difficulty=normal
hardcore=false
pvp=true
force-gamemode=false

# World settings
level-name=world
level-seed=
level-type=minecraft\\:normal
generate-structures=true
spawn-animals=true
spawn-monsters=true
spawn-npcs=true
spawn-protection=16

# Performance
view-distance=10
simulation-distance=10
max-tick-time=60000
max-world-size=29999984

# Network
network-compression-threshold=256
rate-limit=0
online-mode=true
enable-status=true

# RCON (Remote Console for management)
enable-rcon=true
rcon.address=0.0.0.0
rcon.port=25575
rcon.password={rcon_password}
broadcast-rcon-to-ops=true

# Advanced
allow-flight=false
allow-nether=true
enable-command-block=false
operator-permission-level=4
function-permission-level=2
white-list=false
enforce-whitelist=false
resource-pack=
resource-pack-prompt=
require-resource-pack=false
"""
        return properties

    def action_cancel(self) -> None:
        """Handle cancel action (Escape key or Cancel button on step 1)."""
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "back-btn":
            if self.current_step == 1:
                # On first step, Cancel exits the wizard
                self.action_cancel()
            else:
                # On other steps, go back
                self.current_step -= 1
                self.update_step()
        elif event.button.id == "next-btn":
            if self.save_current_step() and self.current_step < self.max_steps:
                self.current_step += 1
                self.update_step()
            elif self.save_current_step():
                # Final step - create server
                self.create_server()

    def save_current_step(self) -> bool:
        """Save data from current step."""
        if self.current_step == 1:
            radio_set = self.query_one("#server-type", ViRadioSet)
            if radio_set.pressed_button:
                button_id = radio_set.pressed_button.id
                if button_id == "vanilla":
                    self.server_data["server_type"] = ServerType.VANILLA
                elif button_id == "forge":
                    self.server_data["server_type"] = ServerType.FORGE
                elif button_id == "fabric":
                    self.server_data["server_type"] = ServerType.FABRIC
                elif button_id == "modpack":
                    self.server_data["server_type"] = ServerType.MODPACK
                return True
            return False
        elif self.current_step == 2:
            # Try Select widget first (success case)
            try:
                version_select = self.query_one("#mc-version-select", Select)
                self.server_data["minecraft_version"] = version_select.value
            except Exception:
                # Fallback to Input widget (error case)
                try:
                    version_input = self.query_one("#mc-version-input", Input)
                    self.server_data["minecraft_version"] = version_input.value
                except Exception:
                    # Still loading or error - keep existing value
                    pass

            if self.server_data["server_type"] == ServerType.FORGE:
                forge_version = self.query_one("#forge-version", Input)
                self.server_data["forge_version"] = forge_version.value or None
            elif self.server_data["server_type"] == ServerType.FABRIC:
                fabric_version = self.query_one("#fabric-version", Input)
                self.server_data["fabric_version"] = fabric_version.value or None
            elif self.server_data["server_type"] == ServerType.MODPACK:
                modpack_url = self.query_one("#modpack-url", Input)
                self.server_data["modpack_url"] = modpack_url.value
            return True
        elif self.current_step == 3:
            from pathlib import Path

            server_name = self.query_one("#server-name", Input)
            max_players = self.query_one("#max-players", Input)
            eula = self.query_one("#eula-checkbox", Checkbox)

            self.server_data["name"] = server_name.value

            # Handle droplet size selection
            size_selector = self.query_one("#droplet-size-selector", ViRadioSet)
            if size_selector.pressed_button:
                button_id = size_selector.pressed_button.id
                # Extract slug from button id (format: "size-{slug}")
                slug = button_id.replace("size-", "")
                self.server_data["droplet_size"] = slug

            # Handle region selection
            region_selector = self.query_one("#region-selector", ViRadioSet)
            if region_selector.pressed_button:
                button_id = region_selector.pressed_button.id
                # Extract slug from button id (format: "region-{slug}")
                slug = button_id.replace("region-", "")
                self.server_data["region"] = slug

            # Handle SSH key selection
            try:
                ssh_selector = self.query_one("#ssh-key-selector", ViRadioSet)
                if ssh_selector.pressed_button:
                    button_id = ssh_selector.pressed_button.id
                    if button_id == "ssh-key-custom":
                        # Custom path selected
                        custom_path = self.query_one("#ssh-key-custom-path", Input)
                        self.server_data["ssh_key_path"] = custom_path.value
                    else:
                        # One of the found keys selected
                        ssh_dir = Path.home() / ".ssh"
                        # Only include public keys that have corresponding private keys
                        ssh_keys = []
                        for pub_key in sorted(ssh_dir.glob("*.pub")):
                            private_key = pub_key.parent / pub_key.stem
                            if private_key.exists():
                                ssh_keys.append(pub_key)
                        # Extract index from button ID (e.g., "ssh-key-0" -> 0)
                        try:
                            key_index = int(button_id.split("-")[-1])
                            if key_index < len(ssh_keys):
                                self.server_data["ssh_key_path"] = str(ssh_keys[key_index])
                        except (ValueError, IndexError):
                            # Invalid index, keep existing value
                            pass
            except Exception:
                # Fallback to direct input if selector not found
                try:
                    ssh_key_input = self.query_one("#ssh-key-path", Input)
                    self.server_data["ssh_key_path"] = ssh_key_input.value
                except Exception:
                    # Keep existing value if no input found
                    pass

            try:
                self.server_data["max_players"] = int(max_players.value)
            except ValueError:
                return False
            self.server_data["accept_eula"] = eula.value

            # Memory is determined by droplet size, use a default
            self.server_data["memory_mb"] = 3072
            return True
        elif self.current_step == 4:
            # Save server.properties content
            properties_editor = self.query_one("#properties-editor", TextArea)
            self.server_data["server_properties_text"] = properties_editor.text
            # Parse properties into a dictionary
            self.server_data["server_properties"] = self.parse_properties(properties_editor.text)
            return True
        return True

    def parse_properties(self, properties_text: str) -> dict:
        """Parse server.properties text into a dictionary.

        Args:
            properties_text: Raw server.properties file content

        Returns:
            Dictionary of property key-value pairs
        """
        properties = {}
        for line in properties_text.split("\n"):
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            # Parse key=value pairs
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # Convert boolean strings
                if value.lower() == "true":
                    properties[key] = True
                elif value.lower() == "false":
                    properties[key] = False
                # Try to convert to int
                elif value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
                    properties[key] = int(value)
                # Keep as string
                else:
                    properties[key] = value
        return properties

    def create_server(self):
        """Create the server."""
        # Create ServerConfig from server_data
        from ..models.server import ServerConfig

        config = ServerConfig(
            name=self.server_data["name"],
            server_type=self.server_data["server_type"],
            minecraft_version=self.server_data["minecraft_version"],
            forge_version=self.server_data.get("forge_version"),
            fabric_version=self.server_data.get("fabric_version"),
            modpack_url=self.server_data.get("modpack_url"),
            max_players=self.server_data["max_players"],
            memory_mb=self.server_data["memory_mb"],
            droplet_size=self.server_data.get("droplet_size", "s-2vcpu-4gb"),
            region=self.server_data.get("region", "nyc3"),
            accept_eula=self.server_data["accept_eula"],
            server_properties=self.server_data.get("server_properties", {}),
        )

        # Push progress screen to show server creation
        from .progress import ProgressScreen

        self.app.push_screen(ProgressScreen(config, ssh_key_path=self.server_data["ssh_key_path"]))
