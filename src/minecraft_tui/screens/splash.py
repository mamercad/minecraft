# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""Splash screen with ASCII art."""

import random

import pyfiglet
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class SplashScreen(Screen):
    """Splash screen shown on startup."""

    def __init__(self):
        super().__init__()
        self.creeper_positions = []

    CSS = """
    SplashScreen {
        height: 100%;
        background: $surface;
    }

    #splash-container {
        width: 100%;
        height: 100%;
        align: center middle;
    }

    #content-box {
        width: auto;
        height: auto;
        layer: above;
    }

    #ascii-art {
        text-align: center;
        color: $accent;
        text-style: bold;
    }

    #tagline {
        text-align: center;
        color: $text-muted;
        margin-top: 2;
    }

    #hint {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }

    .creeper {
        color: $success;
        text-style: bold;
        layer: below;
    }
    """

    @staticmethod
    def get_creeper_art(size: str = "medium") -> str:
        """Get creeper ASCII art in different sizes."""
        if size == "small":
            return """
  ████████
  ██    ██
  ██████
  ██  ██
  ██████
"""
        elif size == "large":
            return """
    ████████████████████
    ████████████████████
    ████          ██████
    ████  ██████  ██████
    ████  ██████  ██████
    ████          ██████
    ████████████████████
    ████  ██████████  ██
    ████  ████  ████  ██
    ██████████  ████████
    ████████████████████
"""
        else:  # medium (default)
            return """
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

    def compose(self) -> ComposeResult:
        """Compose the splash screen."""
        # Generate ASCII art
        ascii_art = pyfiglet.figlet_format("Minecraft TUI", font="slant")

        # Generate random creepers (3-7 creepers)
        num_creepers = random.randint(3, 7)
        creeper_sizes = ["small", "medium", "large"]

        # Create creepers with random positions
        creepers = []
        for i in range(num_creepers):
            size = random.choice(creeper_sizes)
            creeper_art = self.get_creeper_art(size)
            # Random offset in terminal cells (characters)
            # Typical terminal is 80-120 columns, 24-40 rows
            offset_x = random.randint(-10, 60)
            offset_y = random.randint(-5, 20)
            creeper_id = f"creeper-{i}"
            creepers.append((creeper_art, offset_x, offset_y, creeper_id))
            # Store positions for later application in on_mount
            self.creeper_positions.append((creeper_id, offset_x, offset_y))

        with Static(id="splash-container"):
            # Add creepers in the background
            for creeper_art, _, _, creeper_id in creepers:
                yield Static(creeper_art, classes="creeper", id=creeper_id)

            # Main content in front
            with Static(id="content-box"):
                yield Static(ascii_art, id="ascii-art")
                yield Static(
                    "Manage your Minecraft servers on DigitalOcean",
                    id="tagline",
                )
                yield Static(
                    "[dim]Press any key to continue...[/]",
                    id="hint",
                )

    def on_mount(self) -> None:
        """Set timer to auto-dismiss after 3 seconds and position creepers."""
        # Apply creeper positions
        for creeper_id, offset_x, offset_y in self.creeper_positions:
            try:
                creeper = self.query_one(f"#{creeper_id}", Static)
                creeper.styles.offset = (offset_x, offset_y)
            except Exception:
                # If creeper not found, just skip it
                pass

        self.set_timer(3.0, self.dismiss_splash)

    def on_key(self) -> None:
        """Dismiss splash on any key press."""
        self.dismiss_splash()

    def dismiss_splash(self) -> None:
        """Dismiss the splash screen."""
        self.dismiss()
