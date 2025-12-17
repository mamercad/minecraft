"""Minecraft server data models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ServerType(str, Enum):
    """Minecraft server types."""

    VANILLA = "vanilla"
    FORGE = "forge"
    FABRIC = "fabric"
    MODPACK = "modpack"


class MinecraftVersion(BaseModel):
    """Minecraft version information."""

    version: str  # e.g., "1.20.1"
    release_type: str  # "release" or "snapshot"


class ServerConfig(BaseModel):
    """Minecraft server configuration."""

    name: str = Field(..., description="Server name")
    server_type: ServerType
    minecraft_version: str = Field(..., description="Minecraft version (e.g., 1.20.1)")
    forge_version: str | None = Field(None, description="Forge version for Forge servers")
    fabric_version: str | None = Field(None, description="Fabric loader version for Fabric servers")
    modpack_url: str | None = Field(None, description="URL to modpack zip for custom modpacks")

    # Server settings
    max_players: int = Field(default=20, ge=1, le=100)
    server_port: int = Field(default=25565)
    memory_mb: int = Field(default=3072, description="Server RAM in MB")
    droplet_size: str = Field(default="s-2vcpu-4gb", description="DigitalOcean droplet size slug")
    region: str = Field(default="nyc3", description="DigitalOcean region slug")

    # EULA acceptance
    accept_eula: bool = Field(default=False)

    # Additional properties
    server_properties: dict[str, Any] = Field(
        default_factory=lambda: {
            "difficulty": "normal",
            "gamemode": "survival",
            "pvp": True,
            "enable-command-block": False,
        }
    )


class Server(BaseModel):
    """Complete server instance."""

    id: str  # Unique identifier
    config: ServerConfig
    droplet_id: int | None = None
    ip_address: str | None = None
    status: str = "creating"  # creating, running, stopped, error
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
