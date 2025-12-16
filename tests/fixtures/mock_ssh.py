"""Mock fixtures for SSH connections."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_ssh_client():
    """Mock paramiko SSH client."""
    client = MagicMock()
    # Mock exec_command for various commands
    return client
