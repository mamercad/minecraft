"""Mock fixtures for DigitalOcean service."""

import pytest
from unittest.mock import AsyncMock


@pytest.fixture
def mock_do_account_info():
    """Mock DigitalOcean account info."""
    return {
        "email": "user@example.com",
        "uuid": "abc123-def456-ghi789",
        "status": "active",
        "droplet_limit": 25,
        "email_verified": True,
        "team": None,
    }


@pytest.fixture
def mock_do_droplet_list():
    """Mock list of DigitalOcean droplets."""
    return [
        {
            "id": 123456789,
            "name": "crimson-creeper",
            "networks": {
                "v4": [{"type": "public", "ip_address": "10.0.1.42"}]
            },
            "size": {"slug": "s-2vcpu-4gb", "vcpus": 2, "memory": 4096, "disk": 80},
            "region": {"slug": "nyc3", "name": "New York 3"},
            "status": "active",
            "created_at": "2024-03-15T14:32:15Z",
            "tags": ["minecraft-tui", "minecraft-server"],
            "vcpus": 2,
            "memory": 4096,
            "disk": 80,
        },
        {
            "id": 987654321,
            "name": "azure-enderman",
            "networks": {
                "v4": [{"type": "public", "ip_address": "10.0.1.101"}]
            },
            "size": {"slug": "s-2vcpu-4gb", "vcpus": 2, "memory": 4096, "disk": 80},
            "region": {"slug": "sfo3", "name": "San Francisco 3"},
            "status": "active",
            "created_at": "2024-03-14T10:20:30Z",
            "tags": ["minecraft-tui", "minecraft-server"],
            "vcpus": 2,
            "memory": 4096,
            "disk": 80,
        },
        {
            "id": 555555555,
            "name": "golden-villager",
            "networks": {
                "v4": [{"type": "public", "ip_address": "10.0.1.215"}]
            },
            "size": {"slug": "s-4vcpu-8gb", "vcpus": 4, "memory": 8192, "disk": 160},
            "region": {"slug": "ams3", "name": "Amsterdam 3"},
            "status": "active",
            "created_at": "2024-03-10T08:15:45Z",
            "tags": ["minecraft-tui", "minecraft-server"],
            "vcpus": 4,
            "memory": 8192,
            "disk": 160,
        },
    ]


@pytest.fixture
def mock_digitalocean_service(mock_do_account_info, mock_do_droplet_list):
    """Mock DigitalOceanService with common operations."""
    service = AsyncMock()
    service.get_account_info = AsyncMock(return_value=mock_do_account_info)
    service.list_droplets = AsyncMock(return_value=mock_do_droplet_list)
    service.ensure_ssh_key = AsyncMock(return_value=12345)
    return service
