"""Documentation modal screens for README and Changelog."""

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Markdown


class DocsModal(ModalScreen):
    """Modal screen for displaying documentation."""

    BINDINGS = [
        Binding("escape", "close", "Close", priority=True),
        Binding("q", "close", "Close", show=False),
    ]

    CSS = """
    DocsModal {
        align: center middle;
    }

    #docs-container {
        width: 90%;
        height: 90%;
        max-width: 120;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
    }

    #docs-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    #docs-content {
        height: 1fr;
        overflow-y: auto;
        padding: 1;
        background: $background;
        border: solid $primary-darken-2;
    }

    #docs-footer {
        height: auto;
        margin-top: 1;
        align: center middle;
    }
    """

    def __init__(self, title: str, content: str):
        """Initialize the docs modal.

        Args:
            title: Title to display at the top
            content: Markdown content to display
        """
        super().__init__()
        self.doc_title = title
        self.doc_content = content

    def compose(self) -> ComposeResult:
        """Compose the modal."""
        with Container(id="docs-container"):
            yield Label(self.doc_title, id="docs-title")
            with Vertical(id="docs-content"):
                yield Markdown(self.doc_content)
            with Container(id="docs-footer"):
                yield Button("Close (Esc)", variant="primary", id="close-btn")

    def action_close(self) -> None:
        """Close the modal."""
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "close-btn":
            self.dismiss()


class ReadmeModal(DocsModal):
    """Modal for displaying README.md."""

    def __init__(self):
        """Initialize README modal."""
        # Find README.md relative to the package
        readme_path = Path(__file__).parent.parent.parent.parent / "README.md"
        if readme_path.exists():
            content = readme_path.read_text()
        else:
            content = "# README\n\nREADME.md not found."
        super().__init__("📖 README", content)


class ChangelogModal(DocsModal):
    """Modal for displaying CHANGELOG.md."""

    def __init__(self):
        """Initialize Changelog modal."""
        # Find CHANGELOG.md relative to the package
        changelog_path = Path(__file__).parent.parent.parent.parent / "CHANGELOG.md"
        if changelog_path.exists():
            content = changelog_path.read_text()
        else:
            content = "# Changelog\n\nCHANGELOG.md not found."
        super().__init__("📋 Changelog", content)
