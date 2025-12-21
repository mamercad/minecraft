# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""Snapshot tests for welcome screen."""

from textual.app import App
from textual.pilot import Pilot

from minecraft_tui.screens.welcome import WelcomeScreen


def test_welcome_screen_empty(snap_compare):
    """Test welcome screen with empty token input."""

    class TestWelcomeApp(App):
        def on_mount(self):
            self.push_screen(WelcomeScreen())

    assert snap_compare(
        TestWelcomeApp(),
        terminal_size=(100, 30)
    )


def test_welcome_screen_with_token(snap_compare):
    """Test welcome screen with token entered (masked)."""

    async def enter_token(pilot: Pilot):
        # Focus on input and type token
        await pilot.press("tab")  # Focus on input
        await pilot.press(*"dop_v1_1234567890abcdef")
        await pilot.pause()

    class TestWelcomeApp(App):
        def on_mount(self):
            self.push_screen(WelcomeScreen())

    assert snap_compare(
        TestWelcomeApp(),
        run_before=enter_token,
        terminal_size=(100, 30)
    )
