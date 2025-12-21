# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""Snapshot tests for splash screen."""

import random

from textual.app import App

from minecraft_tui.screens.splash import SplashScreen


def test_splash_screen_default(snap_compare):
    """Test splash screen with deterministic creeper layout."""

    class TestSplashApp(App):
        def on_mount(self):
            # Seed random for deterministic creeper generation
            random.seed(42)
            screen = SplashScreen()
            # Disable auto-dismiss timer for snapshot
            screen.set_timer = lambda *_args, **_kwargs: None
            self.push_screen(screen)

    assert snap_compare(
        TestSplashApp(),
        terminal_size=(100, 30)
    )


def test_splash_screen_variant(snap_compare):
    """Test splash screen with different seed for variety."""

    class TestSplashApp(App):
        def on_mount(self):
            # Different seed for different creeper layout
            random.seed(123)
            screen = SplashScreen()
            screen.set_timer = lambda *_args, **_kwargs: None
            self.push_screen(screen)

    assert snap_compare(
        TestSplashApp(),
        terminal_size=(100, 30)
    )
