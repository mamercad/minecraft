"""Mock fixtures for SSH connections."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_ssh_client():
    """Mock paramiko SSH client."""
    client = MagicMock()
    # Mock exec_command for various commands
    return client
