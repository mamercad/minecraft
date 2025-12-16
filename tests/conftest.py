"""Pytest configuration and shared fixtures."""

import os
import pytest
from pathlib import Path

# Import all fixtures from fixtures directory
pytest_plugins = [
    "tests.fixtures.mock_digitalocean",
    "tests.fixtures.mock_ssh",
    "tests.fixtures.mock_rcon",
]


@pytest.fixture
def mock_settings():
    """Mock Settings object for testing."""
    from minecraft_tui.config import Settings
    from pydantic import SecretStr

    return Settings(
        digitalocean_token=SecretStr("test_token_12345"),
        default_region="nyc3",
        default_size="s-2vcpu-4gb",
        default_image="ubuntu-24-04-x64",
        ssh_key_path=Path("/fake/ssh/id_rsa.pub"),
        ssh_private_key_path=Path("/fake/ssh/id_rsa"),
        default_java_version=21,
    )


@pytest.fixture(autouse=True)
def disable_animations():
    """Automatically disable animations in all tests."""
    # This runs for every test automatically
    os.environ["TEXTUAL_ANIMATIONS"] = "none"
    yield
    # Cleanup after test
    if "TEXTUAL_ANIMATIONS" in os.environ:
        del os.environ["TEXTUAL_ANIMATIONS"]
