# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""Welcome screen for initial setup."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Static


class WelcomeScreen(Screen):
    """Welcome screen for initial setup."""

    BINDINGS = [
        # Vi-style navigation
        Binding("j", "focus_next", "Focus Next", show=False),
        Binding("k", "focus_previous", "Focus Previous", show=False),
    ]

    CSS = """
    WelcomeScreen {
        height: 100%;
    }

    #welcome-container {
        width: 100%;
        height: 100%;
        border: solid green;
        padding: 2;
        background: $surface;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    Static {
        margin-bottom: 1;
    }

    Input {
        margin: 1 0;
    }

    Button {
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the welcome screen."""
        yield Header()
        with Container(id="welcome-container"):
            yield Static("Minecraft Server Manager", id="title")
            yield Static("\nWelcome! To get started, please enter your DigitalOcean API token.")
            yield Static(
                "You can create one at: https://cloud.digitalocean.com/account/api/tokens\n"
            )
            yield Input(
                placeholder="Enter DigitalOcean API token",
                password=True,
                id="token-input",
            )
            with Horizontal():
                yield Button("Continue", variant="primary", id="continue-btn")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "continue-btn":
            token_input = self.query_one("#token-input", Input)
            if token_input.value:
                # Save token to environment (in a real app, you'd save to .env file)
                from pydantic import SecretStr

                self.app.settings.digitalocean_token = SecretStr(token_input.value)

                # Navigate to main menu
                from .main_menu import MainMenuScreen

                self.app.switch_screen(MainMenuScreen())
            else:
                token_input.placeholder = "Please enter a token!"
