"""Snapshot tests for main menu screen."""

from unittest.mock import AsyncMock, patch

from textual.app import App
from textual.pilot import Pilot

from minecraft_tui.screens.main_menu import MainMenuScreen


def test_main_menu_with_account(snap_compare, mock_settings, mock_do_account_info):
    """Test main menu with account information loaded."""

    async def wait_for_account_info(pilot: Pilot):
        # Wait for async account info and server fetch to complete
        await pilot.pause(0.5)

    with patch('minecraft_tui.services.digitalocean.DigitalOceanService') as MockService:
        mock_service = AsyncMock()
        mock_service.get_account_info = AsyncMock(return_value=mock_do_account_info)
        mock_service.list_droplets = AsyncMock(return_value=[])
        MockService.return_value = mock_service

        class TestMainMenuApp(App):
            def __init__(self):
                super().__init__()
                self.settings = mock_settings

            def on_mount(self):
                self.push_screen(MainMenuScreen())

        assert snap_compare(
            TestMainMenuApp(),
            run_before=wait_for_account_info,
            terminal_size=(100, 30)
        )


def test_main_menu_account_error(snap_compare, mock_settings):
    """Test main menu with account info fetch error."""

    async def wait_for_error(pilot: Pilot):
        await pilot.pause(0.5)

    with patch('minecraft_tui.services.digitalocean.DigitalOceanService') as MockService:
        mock_service = AsyncMock()
        mock_service.get_account_info = AsyncMock(
            side_effect=Exception("Failed to fetch account")
        )
        mock_service.list_droplets = AsyncMock(return_value=[])
        MockService.return_value = mock_service

        class TestMainMenuApp(App):
            def __init__(self):
                super().__init__()
                self.settings = mock_settings

            def on_mount(self):
                self.push_screen(MainMenuScreen())

        assert snap_compare(
            TestMainMenuApp(),
            run_before=wait_for_error,
            terminal_size=(100, 30)
        )
