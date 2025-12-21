# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""Server status card widget."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static


class ServerCard(Container):
    """Widget displaying server status information."""

    DEFAULT_CSS = """
    ServerCard {
        width: auto;
        height: auto;
        border: solid $accent;
        padding: 1;
        margin: 1;
        background: $surface;
    }

    .server-name {
        text-style: bold;
        color: $accent;
    }

    .server-status-running {
        color: green;
    }

    .server-status-stopped {
        color: red;
    }

    .server-status-starting {
        color: yellow;
    }
    """

    def __init__(self, name: str, status: str, ip_address: str, server_type: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.server_name = name
        self.server_status = status
        self.server_ip = ip_address
        self.server_type = server_type

    def compose(self) -> ComposeResult:
        """Compose the server card."""
        yield Static(self.server_name, classes="server-name")
        yield Static(f"Type: {self.server_type}")

        # Color-coded status
        status_class = f"server-status-{self.server_status.lower()}"
        yield Static(f"Status: {self.server_status}", classes=status_class)

        yield Static(f"IP: {self.server_ip}:25565")
