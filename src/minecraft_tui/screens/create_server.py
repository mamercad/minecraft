"""Server creation wizard screen."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
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

    #modded-config-container {
        height: 1fr;
        min-height: 10;
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
            "is_modded": False,  # Step 1 choice
            "modded_type": None,  # "modpack" or "blank" (Step 2 sub-choice)
            "server_type": ServerType.VANILLA,  # Final server type for installer
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
        """Step 1: Select server type (Vanilla or Modded)."""
        container.mount(Label("What type of server do you want to create?"))
        radio_set = ViRadioSet(id="server-type")
        container.mount(radio_set)
        radio_set.mount(RadioButton("Vanilla Minecraft", id="vanilla", value=True))
        radio_set.mount(RadioButton("Modded Minecraft", id="modded"))

    def show_step_2(self, container: Container):
        """Step 2: Version/modded type selection."""
        if not self.server_data["is_modded"]:
            # Vanilla: Just show Minecraft version
            container.mount(Label("Minecraft Version:", id="mc-version-label"))
            container.mount(Static("Loading versions from Mojang...", id="version-status"))
            self.run_worker(self._load_versions(container), exclusive=False)
        else:
            # Modded: Show sub-choice first
            container.mount(Label("How do you want to set up your modded server?"))
            modded_type_radio = ViRadioSet(id="modded-type")
            container.mount(modded_type_radio)
            current_type = self.server_data.get("modded_type", "modpack")
            modded_type_radio.mount(
                RadioButton(
                    "Install a modpack",
                    id="modded-modpack",
                    value=(current_type == "modpack" or current_type is None),
                )
            )
            modded_type_radio.mount(
                RadioButton(
                    "Blank modded server (no mods, just the loader)",
                    id="modded-blank",
                    value=(current_type == "blank"),
                )
            )

            # Scrollable container for dynamic content based on modded type selection
            container.mount(VerticalScroll(id="modded-config-container"))

            # Show appropriate config based on current selection
            self._update_modded_config()

    def _update_modded_config(self):
        """Update the modded config container based on selected type."""
        try:
            config_container = self.query_one("#modded-config-container", VerticalScroll)
            config_container.remove_children()
        except Exception:
            return

        modded_type = self.server_data.get("modded_type", "modpack")
        if modded_type == "blank":
            self._show_blank_modded_config(config_container)
        else:
            self._show_modpack_config(config_container)

    def _show_modpack_config(self, container: Container):
        """Show modpack configuration options."""
        # Minecraft version selection (can be overridden by CurseForge auto-detect)
        container.mount(Label("Minecraft Version:", id="modpack-mc-version-label"))
        container.mount(Static("Loading versions from Mojang...", id="modpack-mc-version-status"))
        self.run_worker(self._load_modpack_mc_versions(container), exclusive=False)

        # Modpack source selection
        container.mount(Label("Modpack Source:"))
        source_radio = ViRadioSet(id="modpack-source")
        container.mount(source_radio)
        current_source = self.server_data.get("modpack_source", "curseforge")
        source_radio.mount(
            RadioButton(
                "CurseForge URL",
                id="source-curseforge",
                value=(current_source == "curseforge" or current_source is None),
            )
        )
        source_radio.mount(
            RadioButton(
                "Direct ZIP URL",
                id="source-url",
                value=(current_source == "url"),
            )
        )
        source_radio.mount(
            RadioButton(
                "Upload local file",
                id="source-local",
                value=(current_source == "local"),
            )
        )

        # CurseForge API key input (pre-populate from settings if available)
        current_api_key = ""
        if self.app.settings.curseforge_api_key:
            current_api_key = self.app.settings.curseforge_api_key.get_secret_value()
        # Also check server_data in case user already entered a key
        current_api_key = self.server_data.get("curseforge_api_key", current_api_key)

        container.mount(Label("CurseForge API Key:"))
        container.mount(
            Input(
                value=current_api_key,
                placeholder="Get from https://console.curseforge.com",
                id="curseforge-api-key",
                password=True,
            )
        )

        # CurseForge URL input
        container.mount(Label("CurseForge Modpack URL:", id="curseforge-url-label"))
        container.mount(
            Input(
                value=self.server_data.get("curseforge_url", ""),
                placeholder="https://www.curseforge.com/minecraft/modpacks/modpack-name",
                id="curseforge-url",
            )
        )
        container.mount(Static("", id="curseforge-status"))

        # Direct URL input
        container.mount(Label("Direct ZIP URL:", id="modpack-url-label"))
        container.mount(
            Input(
                value=self.server_data.get("modpack_url", ""),
                placeholder="https://example.com/modpack.zip",
                id="modpack-url",
            )
        )

        # Local file input
        container.mount(Label("Local File Path:", id="modpack-file-label"))
        container.mount(
            Input(
                value=self.server_data.get("modpack_file_path", ""),
                placeholder="~/Downloads/modpack.zip",
                id="modpack-file-path",
            )
        )

        container.mount(Label("Modloader (auto-detected for CurseForge, or select manually):"))
        modloader_radio = ViRadioSet(id="modpack-loader")
        container.mount(modloader_radio)
        current_loader = self.server_data.get("modpack_loader", "none")
        modloader_radio.mount(
            RadioButton(
                "None (complete server pack)",
                id="loader-none",
                value=(current_loader == "none" or current_loader is None),
            )
        )
        modloader_radio.mount(
            RadioButton("Forge", id="loader-forge", value=(current_loader == "forge"))
        )
        modloader_radio.mount(
            RadioButton("Fabric", id="loader-fabric", value=(current_loader == "fabric"))
        )
        container.mount(Label("Modloader Version:", id="modpack-loader-version-label"))
        container.mount(
            Static("Select a modloader above to load versions", id="modpack-loader-version-status")
        )
        # Load versions based on current selection
        if current_loader == "forge":
            self.run_worker(self._load_modpack_forge_versions(container), exclusive=False)
        elif current_loader == "fabric":
            self.run_worker(self._load_modpack_fabric_versions(container), exclusive=False)

    def _show_blank_modded_config(self, container: Container):
        """Show blank modded server configuration options."""
        # Minecraft version
        container.mount(Label("Minecraft Version:", id="mc-version-label"))
        container.mount(Static("Loading versions from Mojang...", id="version-status"))
        self.run_worker(self._load_versions(container), exclusive=False)

        # Loader selection
        container.mount(Label("Modloader:"))
        loader_radio = ViRadioSet(id="blank-loader")
        container.mount(loader_radio)
        current_loader = self.server_data.get("blank_loader", "forge")
        loader_radio.mount(
            RadioButton(
                "Forge",
                id="blank-loader-forge",
                value=(current_loader == "forge" or current_loader is None),
            )
        )
        loader_radio.mount(
            RadioButton(
                "Fabric",
                id="blank-loader-fabric",
                value=(current_loader == "fabric"),
            )
        )

        # Loader version
        container.mount(Label("Loader Version:", id="blank-loader-version-label"))
        container.mount(Static("Loading versions...", id="blank-loader-version-status"))

        # Load versions based on current loader selection
        if current_loader == "fabric":
            self.run_worker(self._load_blank_fabric_versions(container), exclusive=False)
        else:
            self.run_worker(self._load_blank_forge_versions(container), exclusive=False)

    async def _load_blank_forge_versions(self, container: Container):
        """Load Forge versions for blank modded server."""
        try:
            from ..services.minecraft.loader_versions import LoaderVersionService

            service = LoaderVersionService()
            mc_version = self.server_data.get("minecraft_version", "1.20.1")
            versions = await service.fetch_forge_versions_detailed(mc_version, limit=15)

            # Remove loading indicator
            try:
                loading = container.query_one("#blank-loader-version-status", Static)
                loading.remove()
            except Exception:
                pass

            # Remove existing select if present
            try:
                existing = container.query_one("#blank-loader-version-select", Select)
                existing.remove()
            except Exception:
                pass

            if versions:
                options = [("latest (auto-detect)", "latest")] + [(v, v) for v in versions]
                select = Select(
                    options=options,
                    value=self.server_data.get("forge_version") or "latest",
                    id="blank-loader-version-select",
                )
                try:
                    label = container.query_one("#blank-loader-version-label", Label)
                    container.mount(select, after=label)
                except Exception:
                    container.mount(select)
            else:
                container.mount(
                    Static(
                        "No Forge versions found for this MC version",
                        id="blank-loader-version-status",
                    )
                )

        except Exception:
            try:
                status = container.query_one("#blank-loader-version-status", Static)
                status.update("[yellow]Could not load Forge versions[/]")
            except Exception:
                pass

    async def _load_blank_fabric_versions(self, container: Container):
        """Load Fabric versions for blank modded server."""
        try:
            from ..services.minecraft.loader_versions import LoaderVersionService

            service = LoaderVersionService()
            versions = await service.fetch_fabric_versions(limit=15)

            # Remove loading indicator
            try:
                loading = container.query_one("#blank-loader-version-status", Static)
                loading.remove()
            except Exception:
                pass

            # Remove existing select if present
            try:
                existing = container.query_one("#blank-loader-version-select", Select)
                existing.remove()
            except Exception:
                pass

            if versions:
                options = [("latest (auto-detect)", "latest")] + [(v, v) for v in versions]
                select = Select(
                    options=options,
                    value=self.server_data.get("fabric_version") or "latest",
                    id="blank-loader-version-select",
                )
                try:
                    label = container.query_one("#blank-loader-version-label", Label)
                    container.mount(select, after=label)
                except Exception:
                    container.mount(select)
            else:
                container.mount(
                    Static("No Fabric versions found", id="blank-loader-version-status")
                )

        except Exception:
            try:
                status = container.query_one("#blank-loader-version-status", Static)
                status.update("[yellow]Could not load Fabric versions[/]")
            except Exception:
                pass

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
        if (
            self.server_data.get("modpack_url")
            or self.server_data.get("modpack_file_path")
            or self.server_data.get("curseforge_url")
        ):
            source = self.server_data.get("modpack_source", "url")
            if source == "curseforge":
                cf_info = self.server_data.get("curseforge_info")
                if cf_info:
                    container.mount(Static(f"CurseForge: {cf_info.name}"))
                else:
                    container.mount(
                        Static(f"CurseForge URL: {self.server_data.get('curseforge_url', 'N/A')}")
                    )
                if self.server_data.get("modpack_url"):
                    container.mount(
                        Static(
                            f"Server Pack URL: {self.server_data.get('modpack_url', 'N/A')[:60]}..."
                        )
                    )
            elif source == "local":
                container.mount(
                    Static(f"Modpack File: {self.server_data.get('modpack_file_path', 'N/A')}")
                )
            else:
                container.mount(
                    Static(f"Modpack URL: {self.server_data.get('modpack_url', 'N/A')}")
                )
            if self.server_data.get("modpack_loader"):
                loader = self.server_data["modpack_loader"].capitalize()
                version = self.server_data.get("modpack_loader_version") or "latest"
                container.mount(Static(f"Modloader: {loader} {version}"))
            else:
                container.mount(Static("Modloader: None (complete server pack)"))
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

            # Mount Select widget after the label
            options = [(v.version, v.version) for v in versions]
            select = Select(
                options=options,
                value=latest,
                id="mc-version-select",
            )
            try:
                label = container.query_one("#mc-version-label", Label)
                container.mount(select, after=label)
            except Exception:
                container.mount(select)

        except Exception:
            # Handle error - show fallback Input
            try:
                loading = container.query_one("#version-status", Static)
                loading.update("[yellow]Could not load versions from Mojang[/]")
            except Exception:
                pass

            # Mount Input as fallback after the label
            input_widget = Input(
                value=self.server_data["minecraft_version"],
                placeholder="e.g., 1.21.11",
                id="mc-version-input",
            )
            try:
                label = container.query_one("#mc-version-label", Label)
                container.mount(input_widget, after=label)
            except Exception:
                container.mount(input_widget)

    async def _load_forge_versions(self, container: Container):
        """Async worker to load Forge versions and mount Select widget."""
        try:
            from ..services.minecraft.loader_versions import LoaderVersionService

            service = LoaderVersionService()
            mc_version = self.server_data.get("minecraft_version", "1.20.1")
            versions = await service.fetch_forge_versions_detailed(mc_version, limit=15)

            # Remove loading indicator
            try:
                loading = container.query_one("#forge-version-status", Static)
                loading.remove()
            except Exception:
                pass

            if versions:
                # Mount Select widget after the label
                options = [("latest (auto-detect)", "latest")] + [(v, v) for v in versions]
                select = Select(
                    options=options,
                    value="latest",
                    id="forge-version-select",
                )
                try:
                    label = container.query_one("#forge-version-label", Label)
                    container.mount(select, after=label)
                except Exception:
                    container.mount(select)
            else:
                # No versions found, show input fallback
                input_widget = Input(
                    value=self.server_data.get("forge_version", ""),
                    placeholder="e.g., 47.2.0 (or 'latest')",
                    id="forge-version",
                )
                try:
                    label = container.query_one("#forge-version-label", Label)
                    container.mount(input_widget, after=label)
                except Exception:
                    container.mount(input_widget)

        except Exception:
            # Handle error - show fallback Input
            try:
                loading = container.query_one("#forge-version-status", Static)
                loading.update("[yellow]Could not load Forge versions[/]")
            except Exception:
                pass

            input_widget = Input(
                value=self.server_data.get("forge_version", ""),
                placeholder="e.g., 47.2.0 (or 'latest')",
                id="forge-version",
            )
            try:
                label = container.query_one("#forge-version-label", Label)
                container.mount(input_widget, after=label)
            except Exception:
                container.mount(input_widget)

    async def _load_fabric_versions(self, container: Container):
        """Async worker to load Fabric versions and mount Select widget."""
        try:
            from ..services.minecraft.loader_versions import LoaderVersionService

            service = LoaderVersionService()
            versions = await service.fetch_fabric_versions(limit=15)

            # Remove loading indicator
            try:
                loading = container.query_one("#fabric-version-status", Static)
                loading.remove()
            except Exception:
                pass

            if versions:
                # Mount Select widget after the label
                options = [("latest (auto-detect)", "latest")] + [(v, v) for v in versions]
                select = Select(
                    options=options,
                    value="latest",
                    id="fabric-version-select",
                )
                try:
                    label = container.query_one("#fabric-version-label", Label)
                    container.mount(select, after=label)
                except Exception:
                    container.mount(select)
            else:
                # No versions found, show input fallback
                input_widget = Input(
                    value=self.server_data.get("fabric_version", ""),
                    placeholder="e.g., 0.16.0 (or 'latest')",
                    id="fabric-version",
                )
                try:
                    label = container.query_one("#fabric-version-label", Label)
                    container.mount(input_widget, after=label)
                except Exception:
                    container.mount(input_widget)

        except Exception:
            # Handle error - show fallback Input
            try:
                loading = container.query_one("#fabric-version-status", Static)
                loading.update("[yellow]Could not load Fabric versions[/]")
            except Exception:
                pass

            input_widget = Input(
                value=self.server_data.get("fabric_version", ""),
                placeholder="e.g., 0.16.0 (or 'latest')",
                id="fabric-version",
            )
            try:
                label = container.query_one("#fabric-version-label", Label)
                container.mount(input_widget, after=label)
            except Exception:
                container.mount(input_widget)

    async def _load_modpack_forge_versions(self, container: Container):
        """Load Forge versions for modpack loader selection."""
        try:
            from ..services.minecraft.loader_versions import LoaderVersionService

            # Update status
            try:
                status = container.query_one("#modpack-loader-version-status", Static)
                status.update("Loading Forge versions...")
            except Exception:
                pass

            service = LoaderVersionService()
            mc_version = self.server_data.get("minecraft_version", "1.20.1")
            versions = await service.fetch_forge_versions_detailed(mc_version, limit=15)

            # Remove status and add select
            try:
                status = container.query_one("#modpack-loader-version-status", Static)
                status.remove()
            except Exception:
                pass

            # Remove existing select if present
            try:
                existing = container.query_one("#modpack-loader-version-select", Select)
                existing.remove()
            except Exception:
                pass

            if versions:
                # Format is (label, value)
                options = [("latest (auto-detect)", "latest")] + [(v, v) for v in versions]
                select = Select(
                    options=options,
                    value=self.server_data.get("modpack_loader_version") or "latest",
                    id="modpack-loader-version-select",
                )
                container.mount(select)
            else:
                container.mount(
                    Static(
                        "No Forge versions found for this MC version",
                        id="modpack-loader-version-status",
                    )
                )

        except Exception:
            try:
                status = container.query_one("#modpack-loader-version-status", Static)
                status.update("[yellow]Could not load Forge versions[/]")
            except Exception:
                pass

    async def _load_modpack_fabric_versions(self, container: Container):
        """Load Fabric versions for modpack loader selection."""
        try:
            from ..services.minecraft.loader_versions import LoaderVersionService

            # Update status
            try:
                status = container.query_one("#modpack-loader-version-status", Static)
                status.update("Loading Fabric versions...")
            except Exception:
                pass

            service = LoaderVersionService()
            versions = await service.fetch_fabric_versions(limit=15)

            # Remove status and add select
            try:
                status = container.query_one("#modpack-loader-version-status", Static)
                status.remove()
            except Exception:
                pass

            # Remove existing select if present
            try:
                existing = container.query_one("#modpack-loader-version-select", Select)
                existing.remove()
            except Exception:
                pass

            if versions:
                # Format is (label, value)
                options = [("latest (auto-detect)", "latest")] + [(v, v) for v in versions]
                select = Select(
                    options=options,
                    value=self.server_data.get("modpack_loader_version") or "latest",
                    id="modpack-loader-version-select",
                )
                container.mount(select)
            else:
                container.mount(
                    Static("No Fabric versions found", id="modpack-loader-version-status")
                )

        except Exception:
            try:
                status = container.query_one("#modpack-loader-version-status", Static)
                status.update("[yellow]Could not load Fabric versions[/]")
            except Exception:
                pass

    async def _load_modpack_mc_versions(self, container: Container):
        """Async worker to load Minecraft versions for modpack config."""
        try:
            from ..services.minecraft.version_service import MinecraftVersionService

            service = MinecraftVersionService()
            versions = await service.fetch_versions(limit=20)
            latest = await service.get_latest_release()

            # Remove loading indicator
            try:
                loading = container.query_one("#modpack-mc-version-status", Static)
                loading.remove()
            except Exception:
                pass

            # Remove existing select if present
            try:
                existing = container.query_one("#modpack-mc-version-select", Select)
                existing.remove()
            except Exception:
                pass

            # Mount Select widget after the label
            options = [(v.version, v.version) for v in versions]
            current_version = self.server_data.get("minecraft_version", latest)
            select = Select(
                options=options,
                value=current_version,
                id="modpack-mc-version-select",
            )
            try:
                label = container.query_one("#modpack-mc-version-label", Label)
                container.mount(select, after=label)
            except Exception:
                container.mount(select)

        except Exception:
            # Handle error - show fallback Input
            try:
                loading = container.query_one("#modpack-mc-version-status", Static)
                loading.update("[yellow]Could not load versions from Mojang[/]")
            except Exception:
                pass

            # Mount Input as fallback after the label
            input_widget = Input(
                value=self.server_data.get("minecraft_version", "1.20.1"),
                placeholder="e.g., 1.20.1",
                id="modpack-mc-version-input",
            )
            try:
                label = container.query_one("#modpack-mc-version-label", Label)
                container.mount(input_widget, after=label)
            except Exception:
                container.mount(input_widget)

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

    def on_input_changed(self, event) -> None:
        """Handle input changes."""
        # Check if this is the CurseForge URL input
        if event.input.id == "curseforge-url" and self.current_step == 2:
            url = event.value.strip()
            # Debounce - only fetch if URL looks complete
            if (
                url
                and "curseforge.com" in url
                and "/modpacks/" in url
                and len(url.split("/")[-1]) > 2
            ):
                self.run_worker(
                    self._fetch_curseforge_info(url), exclusive=True, group="curseforge"
                )

        # Re-fetch when API key changes and URL is already entered
        if event.input.id == "curseforge-api-key" and self.current_step == 2:
            try:
                url_input = self.query_one("#curseforge-url", Input)
                url = url_input.value.strip()
                if (
                    url
                    and "curseforge.com" in url
                    and "/modpacks/" in url
                    and len(url.split("/")[-1]) > 2
                ):
                    self.run_worker(
                        self._fetch_curseforge_info(url), exclusive=True, group="curseforge"
                    )
            except Exception:
                pass

    async def _fetch_curseforge_info(self, url: str) -> None:
        """Fetch modpack info from CurseForge URL."""
        try:
            status = self.query_one("#curseforge-status", Static)
            status.update("[yellow]Fetching modpack info...[/]")

            # Check for API key - first from input field, then from settings
            api_key_value = None
            try:
                api_key_input = self.query_one("#curseforge-api-key", Input)
                if api_key_input.value.strip():
                    api_key_value = api_key_input.value.strip()
                    # Save to server_data for later use
                    self.server_data["curseforge_api_key"] = api_key_value
            except Exception:
                pass

            # Fall back to settings if no input value
            if not api_key_value and self.app.settings.curseforge_api_key:
                api_key_value = self.app.settings.curseforge_api_key.get_secret_value()

            if not api_key_value:
                status.update(
                    "[red]Enter your CurseForge API key above. "
                    "Get one from https://console.curseforge.com[/]"
                )
                return

            from ..services.curseforge import CurseForgeService

            service = CurseForgeService(api_key_value)
            info = await service.fetch_from_url(url)

            # Update status with modpack info
            status.update(
                f"[green]✓ {info.name}[/] - "
                f"MC {info.minecraft_version or '?'}, "
                f"{info.modloader or 'unknown loader'}"
            )

            # Auto-populate fields
            self.server_data["curseforge_url"] = url
            self.server_data["curseforge_info"] = info

            if info.server_pack_url:
                self.server_data["modpack_url"] = info.server_pack_url
                try:
                    url_input = self.query_one("#modpack-url", Input)
                    url_input.value = info.server_pack_url
                except Exception:
                    pass

            if info.minecraft_version:
                self.server_data["minecraft_version"] = info.minecraft_version
                # Update the MC version select widget
                try:
                    mc_select = self.query_one("#modpack-mc-version-select", Select)
                    mc_select.value = info.minecraft_version
                except Exception:
                    try:
                        mc_input = self.query_one("#modpack-mc-version-input", Input)
                        mc_input.value = info.minecraft_version
                    except Exception:
                        pass

            # Auto-select modloader
            if info.modloader:
                self.server_data["modpack_loader"] = info.modloader
                try:
                    loader_radio = self.query_one("#modpack-loader", ViRadioSet)
                    for button in loader_radio.query("RadioButton"):
                        if button.id == f"loader-{info.modloader}":
                            button.value = True
                            # Trigger version loading
                            try:
                                container = self.query_one(
                                    "#modded-config-container", VerticalScroll
                                )
                            except Exception:
                                container = self.query_one("#step-content", Container)
                            if info.modloader == "forge":
                                self.run_worker(
                                    self._load_modpack_forge_versions(container),
                                    exclusive=False,
                                )
                            elif info.modloader == "fabric":
                                self.run_worker(
                                    self._load_modpack_fabric_versions(container),
                                    exclusive=False,
                                )
                            break
                except Exception:
                    pass

        except Exception as e:
            try:
                status = self.query_one("#curseforge-status", Static)
                status.update(f"[red]Error: {e}[/]")
            except Exception:
                pass

    def on_radio_set_changed(self, event) -> None:
        """Handle radio set changes."""
        pressed = event.pressed
        if not pressed:
            return

        # Handle modded type selection (modpack vs blank)
        if event.radio_set.id == "modded-type" and self.current_step == 2:
            if pressed.id == "modded-modpack":
                self.server_data["modded_type"] = "modpack"
            elif pressed.id == "modded-blank":
                self.server_data["modded_type"] = "blank"
            self._update_modded_config()

        # Handle blank loader selection (forge vs fabric)
        elif event.radio_set.id == "blank-loader" and self.current_step == 2:
            try:
                config_container = self.query_one("#modded-config-container", VerticalScroll)
            except Exception:
                return

            if pressed.id == "blank-loader-forge":
                self.server_data["blank_loader"] = "forge"
                self.run_worker(self._load_blank_forge_versions(config_container), exclusive=False)
            elif pressed.id == "blank-loader-fabric":
                self.server_data["blank_loader"] = "fabric"
                self.run_worker(self._load_blank_fabric_versions(config_container), exclusive=False)

        # Handle modpack loader selector
        elif event.radio_set.id == "modpack-loader" and self.current_step == 2:
            try:
                config_container = self.query_one("#modded-config-container", VerticalScroll)
            except Exception:
                return

            if pressed.id == "loader-forge":
                self.server_data["modpack_loader"] = "forge"
                self.run_worker(
                    self._load_modpack_forge_versions(config_container), exclusive=False
                )
            elif pressed.id == "loader-fabric":
                self.server_data["modpack_loader"] = "fabric"
                self.run_worker(
                    self._load_modpack_fabric_versions(config_container), exclusive=False
                )
            else:
                self.server_data["modpack_loader"] = None
                # None selected - remove version selector and show status
                try:
                    existing = config_container.query_one("#modpack-loader-version-select", Select)
                    existing.remove()
                except Exception:
                    pass
                try:
                    status = config_container.query_one("#modpack-loader-version-status", Static)
                    status.update("Select a modloader above to load versions")
                except Exception:
                    config_container.mount(
                        Static(
                            "Select a modloader above to load versions",
                            id="modpack-loader-version-status",
                        )
                    )

    def on_select_changed(self, event) -> None:
        """Handle select widget changes."""
        select_id = event.select.id
        value = event.value

        # Handle Minecraft version change in modpack config
        if select_id == "modpack-mc-version-select" and self.current_step == 2:
            self.server_data["minecraft_version"] = value
            # Reload loader versions for the new MC version if a loader is selected
            current_loader = self.server_data.get("modpack_loader")
            if current_loader:
                try:
                    config_container = self.query_one("#modded-config-container", VerticalScroll)
                    if current_loader == "forge":
                        self.run_worker(
                            self._load_modpack_forge_versions(config_container), exclusive=False
                        )
                    elif current_loader == "fabric":
                        self.run_worker(
                            self._load_modpack_fabric_versions(config_container), exclusive=False
                        )
                except Exception:
                    pass

        # Handle Minecraft version change in blank modded config
        elif select_id == "mc-version-select" and self.current_step == 2:
            self.server_data["minecraft_version"] = value
            # Reload loader versions for the new MC version
            if self.server_data.get("modded_type") == "blank":
                current_loader = self.server_data.get("blank_loader", "forge")
                try:
                    config_container = self.query_one("#modded-config-container", VerticalScroll)
                    if current_loader == "forge":
                        self.run_worker(
                            self._load_blank_forge_versions(config_container), exclusive=False
                        )
                    elif current_loader == "fabric":
                        self.run_worker(
                            self._load_blank_fabric_versions(config_container), exclusive=False
                        )
                except Exception:
                    pass

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
            # Step 1: Vanilla vs Modded
            radio_set = self.query_one("#server-type", ViRadioSet)
            if radio_set.pressed_button:
                button_id = radio_set.pressed_button.id
                self.server_data["is_modded"] = button_id == "modded"
                if button_id == "vanilla":
                    self.server_data["server_type"] = ServerType.VANILLA
                return True
            return False

        elif self.current_step == 2:
            if not self.server_data["is_modded"]:
                # Vanilla: Just save MC version
                self.server_data["server_type"] = ServerType.VANILLA
                try:
                    version_select = self.query_one("#mc-version-select", Select)
                    self.server_data["minecraft_version"] = version_select.value
                except Exception:
                    try:
                        version_input = self.query_one("#mc-version-input", Input)
                        self.server_data["minecraft_version"] = version_input.value
                    except Exception:
                        pass
            else:
                # Modded: Save modded type and appropriate config
                modded_type = self.server_data.get("modded_type", "modpack")

                if modded_type == "blank":
                    # Blank modded server
                    # Save MC version
                    try:
                        version_select = self.query_one("#mc-version-select", Select)
                        self.server_data["minecraft_version"] = version_select.value
                    except Exception:
                        try:
                            version_input = self.query_one("#mc-version-input", Input)
                            self.server_data["minecraft_version"] = version_input.value
                        except Exception:
                            pass

                    # Save loader type and set server_type
                    blank_loader = self.server_data.get("blank_loader", "forge")
                    if blank_loader == "fabric":
                        self.server_data["server_type"] = ServerType.FABRIC
                        # Save fabric version
                        try:
                            version_select = self.query_one("#blank-loader-version-select", Select)
                            value = version_select.value
                            self.server_data["fabric_version"] = (
                                None if value == "latest" else value
                            )
                        except Exception:
                            self.server_data["fabric_version"] = None
                    else:
                        self.server_data["server_type"] = ServerType.FORGE
                        # Save forge version
                        try:
                            version_select = self.query_one("#blank-loader-version-select", Select)
                            value = version_select.value
                            self.server_data["forge_version"] = None if value == "latest" else value
                        except Exception:
                            self.server_data["forge_version"] = None

                else:
                    # Modpack installation
                    self.server_data["server_type"] = ServerType.MODPACK

                    # Save Minecraft version
                    try:
                        version_select = self.query_one("#modpack-mc-version-select", Select)
                        self.server_data["minecraft_version"] = version_select.value
                    except Exception:
                        try:
                            version_input = self.query_one("#modpack-mc-version-input", Input)
                            self.server_data["minecraft_version"] = version_input.value
                        except Exception:
                            pass

                    # Save source selection
                    try:
                        source_selector = self.query_one("#modpack-source", ViRadioSet)
                        if source_selector.pressed_button:
                            button_id = source_selector.pressed_button.id
                            if button_id == "source-local":
                                self.server_data["modpack_source"] = "local"
                            elif button_id == "source-curseforge":
                                self.server_data["modpack_source"] = "curseforge"
                            else:
                                self.server_data["modpack_source"] = "url"
                    except Exception:
                        pass

                    # Save CurseForge URL
                    try:
                        curseforge_url = self.query_one("#curseforge-url", Input)
                        self.server_data["curseforge_url"] = curseforge_url.value or None
                    except Exception:
                        pass

                    # Save modpack URL
                    try:
                        modpack_url = self.query_one("#modpack-url", Input)
                        self.server_data["modpack_url"] = modpack_url.value or None
                    except Exception:
                        pass

                    # Save modpack file path
                    try:
                        modpack_file_path = self.query_one("#modpack-file-path", Input)
                        self.server_data["modpack_file_path"] = modpack_file_path.value or None
                    except Exception:
                        pass

                    # Save modloader selection
                    try:
                        modloader_selector = self.query_one("#modpack-loader", ViRadioSet)
                        if modloader_selector.pressed_button:
                            button_id = modloader_selector.pressed_button.id
                            if button_id == "loader-forge":
                                self.server_data["modpack_loader"] = "forge"
                            elif button_id == "loader-fabric":
                                self.server_data["modpack_loader"] = "fabric"
                            else:
                                self.server_data["modpack_loader"] = None
                    except Exception:
                        pass

                    # Save modloader version
                    try:
                        version_select = self.query_one("#modpack-loader-version-select", Select)
                        value = version_select.value
                        self.server_data["modpack_loader_version"] = (
                            None if value == "latest" else value
                        )
                    except Exception:
                        self.server_data["modpack_loader_version"] = None

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
            modpack_file_path=self.server_data.get("modpack_file_path"),
            modpack_loader=self.server_data.get("modpack_loader"),
            modpack_loader_version=self.server_data.get("modpack_loader_version"),
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
