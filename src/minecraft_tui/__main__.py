"""Entry point for the Minecraft TUI application."""

import sys

from .app import MinecraftTUI


def main():
    """Run the Minecraft Server Manager TUI."""
    app = MinecraftTUI()
    app.run()


if __name__ == "__main__":
    sys.exit(main())
