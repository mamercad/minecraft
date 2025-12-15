"""Progress log widget for installation progress."""

from textual.widgets import RichLog


class ProgressLog(RichLog):
    """Widget for displaying installation progress with rich text."""

    DEFAULT_CSS = """
    ProgressLog {
        background: $surface;
        color: $text;
        border: solid $accent;
        height: 20;
        scrollbar-size: 1 1;
    }
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auto_scroll = True

    def log_progress(self, message: str):
        """Log a progress message.

        Args:
            message: Progress message to log
        """
        self.write(message)
