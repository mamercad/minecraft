# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""DigitalOcean droplet data models."""

from pydantic import BaseModel, Field


class DropletInfo(BaseModel):
    """DigitalOcean droplet information."""

    id: int
    name: str
    status: str  # new, active, off, archive
    created_at: str
    region: str
    size: str
    image: str
    ip_address: str | None = None
    ipv6_address: str | None = None
    tags: list[str] = Field(default_factory=list)


class DropletCreateRequest(BaseModel):
    """Request model for creating a new droplet."""

    name: str
    region: str
    size: str
    image: str
    ssh_keys: list[int]
    backups: bool = False
    ipv6: bool = True
    monitoring: bool = True
    tags: list[str] = Field(default_factory=lambda: ["minecraft-tui", "minecraft-server"])
    user_data: str | None = None
