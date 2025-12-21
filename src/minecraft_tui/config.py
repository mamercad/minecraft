# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""Configuration management using Pydantic Settings."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # DigitalOcean settings
    digitalocean_token: SecretStr | None = Field(default=None, description="DigitalOcean API token")

    # Default droplet settings
    default_region: str = Field(default="nyc3", description="Default DigitalOcean region")

    default_size: str = Field(
        default="s-2vcpu-4gb",
        description="Default droplet size (Minecraft needs at least 2GB RAM)",
    )

    default_image: str = Field(default="ubuntu-24-04-x64", description="Default Ubuntu image")

    # SSH settings
    ssh_key_path: Path = Field(
        default=Path.home() / ".ssh" / "id_rsa.pub",
        description="Path to SSH public key",
    )

    ssh_private_key_path: Path = Field(
        default=Path.home() / ".ssh" / "id_rsa",
        description="Path to SSH private key",
    )

    # Minecraft settings
    default_java_version: str = Field(
        default="21", description="Default Java version for Minecraft servers"
    )

    # CurseForge API settings
    curseforge_api_key: SecretStr | None = Field(
        default=None,
        description="CurseForge API key from https://console.curseforge.com",
    )

    # Application settings
    config_dir: Path = Field(
        default=Path.home() / ".config" / "minecraft-tui",
        description="Configuration directory",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
