# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""Mock fixtures for RCON service."""

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_rcon_success():
    """Mock successful RCON connection."""
    service = AsyncMock()
    service.get_rcon_password_from_server = AsyncMock(return_value="test_password_123")
    service.connect = AsyncMock()
    service.send_command = AsyncMock(return_value="There are 0 of a max of 20 players online:")
    service.get_server_logs = AsyncMock(return_value=[
        "[14:45:23] [Server thread/INFO]: Starting minecraft server version 1.21.1",
        "[14:45:23] [Server thread/INFO]: Loading properties",
        "[14:45:23] [Server thread/INFO]: Default game type: SURVIVAL",
        "[14:45:24] [Server thread/INFO]: Starting Minecraft server on *:25565",
        "[14:45:32] [Server thread/INFO]: Done (9.543s)! For help, type \"help\"",
        "[14:45:32] [Server thread/INFO]: RCON running on 0.0.0.0:25575",
    ])
    return service


@pytest.fixture
def mock_rcon_connection_refused():
    """Mock RCON connection refused error."""
    service = AsyncMock()
    service.get_rcon_password_from_server = AsyncMock(return_value="test_password_123")
    service.connect = AsyncMock(
        side_effect=ConnectionRefusedError("[Errno 111] Connection refused")
    )
    return service


@pytest.fixture
def mock_rcon_timeout():
    """Mock RCON connection timeout."""
    service = AsyncMock()
    service.get_rcon_password_from_server = AsyncMock(return_value="test_password_123")
    service.connect = AsyncMock(side_effect=TimeoutError("Connection timed out"))
    return service
