"""Server creation wizard screen."""


from textual.app import ComposeResult
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
    RadioSet,
    Static,
)

from ..models.server import ServerType


class CreateServerScreen(Screen):
    """Multi-step server creation wizard."""

    CSS = """
    CreateServerScreen {
        align: center middle;
    }

    #wizard-container {
        width: 80;
        height: auto;
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
        min-height: 20;
        padding: 1;
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
    """

    def __init__(self):
        super().__init__()
        self.current_step = 1
        self.max_steps = 4
        self.server_data = {
            "server_type": None,
            "minecraft_version": "1.20.1",
            "forge_version": None,
            "modpack_url": None,
            "name": "",
            "max_players": 20,
            "memory_mb": 3072,
            "accept_eula": False,
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

        # Update button visibility
        back_btn = self.query_one("#back-btn", Button)
        next_btn = self.query_one("#next-btn", Button)

        back_btn.disabled = self.current_step == 1
        next_btn.label = "Create Server" if self.current_step == self.max_steps else "Next"

    def show_step_1(self, container: Container):
        """Step 1: Select server type."""
        container.mount(Label("Select Server Type:"))
        radio_set = RadioSet(id="server-type")
        radio_set.mount(RadioButton("Vanilla Minecraft", id="vanilla"))
        radio_set.mount(RadioButton("Forge (Modded)", id="forge"))
        radio_set.mount(RadioButton("Custom Modpack", id="modpack"))
        container.mount(radio_set)

    def show_step_2(self, container: Container):
        """Step 2: Version selection."""
        container.mount(Label("Server Configuration:"))
        container.mount(Label("Minecraft Version:"))
        container.mount(
            Input(
                value=self.server_data["minecraft_version"],
                placeholder="e.g., 1.20.1",
                id="mc-version",
            )
        )

        if self.server_data["server_type"] == ServerType.FORGE:
            container.mount(Label("Forge Version:"))
            container.mount(
                Input(
                    value=self.server_data.get("forge_version", ""),
                    placeholder="e.g., 47.2.0 (or leave empty for latest)",
                    id="forge-version",
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

        container.mount(Label("Memory (MB):"))
        container.mount(
            Input(
                value=str(self.server_data["memory_mb"]),
                placeholder="3072",
                id="memory",
            )
        )

        container.mount(Checkbox("I accept the Minecraft EULA", id="eula-checkbox"))

    def show_step_4(self, container: Container):
        """Step 4: Review and confirm."""
        container.mount(Label("Review Server Configuration:"))
        container.mount(Static(f"Server Type: {self.server_data['server_type']}"))
        container.mount(Static(f"Minecraft Version: {self.server_data['minecraft_version']}"))
        if self.server_data.get("forge_version"):
            container.mount(Static(f"Forge Version: {self.server_data['forge_version']}"))
        if self.server_data.get("modpack_url"):
            container.mount(Static(f"Modpack URL: {self.server_data['modpack_url']}"))
        container.mount(Static(f"Server Name: {self.server_data['name']}"))
        container.mount(Static(f"Max Players: {self.server_data['max_players']}"))
        container.mount(Static(f"Memory: {self.server_data['memory_mb']} MB"))
        container.mount(Static(f"EULA Accepted: {self.server_data['accept_eula']}"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "back-btn":
            if self.current_step > 1:
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
            radio_set = self.query_one("#server-type", RadioSet)
            if radio_set.pressed_button:
                button_id = radio_set.pressed_button.id
                if button_id == "vanilla":
                    self.server_data["server_type"] = ServerType.VANILLA
                elif button_id == "forge":
                    self.server_data["server_type"] = ServerType.FORGE
                elif button_id == "modpack":
                    self.server_data["server_type"] = ServerType.MODPACK
                return True
            return False
        elif self.current_step == 2:
            mc_version = self.query_one("#mc-version", Input)
            self.server_data["minecraft_version"] = mc_version.value

            if self.server_data["server_type"] == ServerType.FORGE:
                forge_version = self.query_one("#forge-version", Input)
                self.server_data["forge_version"] = forge_version.value or None
            elif self.server_data["server_type"] == ServerType.MODPACK:
                modpack_url = self.query_one("#modpack-url", Input)
                self.server_data["modpack_url"] = modpack_url.value
            return True
        elif self.current_step == 3:
            server_name = self.query_one("#server-name", Input)
            max_players = self.query_one("#max-players", Input)
            memory = self.query_one("#memory", Input)
            eula = self.query_one("#eula-checkbox", Checkbox)

            self.server_data["name"] = server_name.value
            try:
                self.server_data["max_players"] = int(max_players.value)
                self.server_data["memory_mb"] = int(memory.value)
            except ValueError:
                return False
            self.server_data["accept_eula"] = eula.value
            return True
        return True

    def create_server(self):
        """Create the server."""
        # This would actually create the server
        # For now, just show a message and go back to main menu
        self.app.notify(f"Creating server: {self.server_data['name']}")

        # In a full implementation, this would:
        # 1. Create ServerConfig from server_data
        # 2. Create DigitalOcean droplet
        # 3. Wait for droplet to become active
        # 4. SSH to droplet and install Minecraft
        # 5. Show progress in a separate screen

        self.app.pop_screen()
