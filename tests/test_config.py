# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""Tests for configuration module."""

from pathlib import Path

from minecraft_tui.config import Settings


def test_settings_defaults():
    """Test that settings have correct defaults."""
    settings = Settings()

    assert settings.default_region == "nyc3"
    assert settings.default_size == "s-2vcpu-4gb"
    assert settings.default_image == "ubuntu-24-04-x64"
    assert settings.default_java_version == "21"


def test_settings_with_token():
    """Test settings with DigitalOcean token."""
    settings = Settings(digitalocean_token="test_token")

    assert settings.digitalocean_token is not None
    assert settings.digitalocean_token.get_secret_value() == "test_token"


def test_settings_ssh_key_paths():
    """Test SSH key path defaults."""
    settings = Settings()

    assert settings.ssh_key_path == Path.home() / ".ssh" / "id_rsa.pub"
    assert settings.ssh_private_key_path == Path.home() / ".ssh" / "id_rsa"


def test_settings_config_dir_created():
    """Test that config directory is created."""
    settings = Settings()

    assert settings.config_dir.exists()
    assert settings.config_dir.is_dir()
