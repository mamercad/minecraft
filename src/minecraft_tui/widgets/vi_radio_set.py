"""RadioSet widget with vi key bindings."""

from textual.binding import Binding
from textual.widgets import RadioSet


class ViRadioSet(RadioSet):
    """RadioSet with vi key navigation (j/k)."""

    BINDINGS = [
        Binding("j", "cursor_down", "Next", show=False),
        Binding("k", "cursor_up", "Previous", show=False),
    ]
