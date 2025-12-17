"""Tests for data models."""

from minecraft_tui.models.droplet import DropletCreateRequest, DropletInfo
from minecraft_tui.models.server import Server, ServerConfig, ServerType


def test_server_type_enum():
    """Test ServerType enum values."""
    assert ServerType.VANILLA == "vanilla"
    assert ServerType.FORGE == "forge"
    assert ServerType.FABRIC == "fabric"
    assert ServerType.MODPACK == "modpack"


def test_server_config_vanilla():
    """Test vanilla server configuration."""
    config = ServerConfig(
        name="Test Server",
        server_type=ServerType.VANILLA,
        minecraft_version="1.20.1",
        accept_eula=True,
    )

    assert config.name == "Test Server"
    assert config.server_type == ServerType.VANILLA
    assert config.minecraft_version == "1.20.1"
    assert config.max_players == 20
    assert config.memory_mb == 3072
    assert config.accept_eula is True


def test_server_config_forge():
    """Test Forge server configuration."""
    config = ServerConfig(
        name="Forge Server",
        server_type=ServerType.FORGE,
        minecraft_version="1.20.1",
        forge_version="47.2.0",
        accept_eula=True,
    )

    assert config.server_type == ServerType.FORGE
    assert config.forge_version == "47.2.0"


def test_server_config_fabric():
    """Test Fabric server configuration."""
    config = ServerConfig(
        name="Fabric Server",
        server_type=ServerType.FABRIC,
        minecraft_version="1.20.1",
        fabric_version="0.16.0",
        accept_eula=True,
    )

    assert config.server_type == ServerType.FABRIC
    assert config.fabric_version == "0.16.0"


def test_server_config_modpack():
    """Test modpack server configuration."""
    config = ServerConfig(
        name="Modpack Server",
        server_type=ServerType.MODPACK,
        minecraft_version="1.20.1",
        modpack_url="https://example.com/modpack.zip",
        accept_eula=True,
    )

    assert config.server_type == ServerType.MODPACK
    assert config.modpack_url == "https://example.com/modpack.zip"


def test_server_config_validation():
    """Test server configuration validation."""
    # Should succeed with required fields
    config = ServerConfig(name="Test", server_type=ServerType.VANILLA, minecraft_version="1.20.1")
    assert config.name == "Test"


def test_server_model():
    """Test complete server model."""
    config = ServerConfig(
        name="Test Server",
        server_type=ServerType.VANILLA,
        minecraft_version="1.20.1",
    )

    server = Server(id="test-123", config=config)

    assert server.id == "test-123"
    assert server.config.name == "Test Server"
    assert server.status == "creating"
    assert server.droplet_id is None
    assert server.ip_address is None


def test_droplet_info():
    """Test droplet information model."""
    droplet = DropletInfo(
        id=12345,
        name="minecraft-server",
        status="active",
        created_at="2024-01-01T00:00:00Z",
        region="nyc3",
        size="s-2vcpu-4gb",
        image="ubuntu-24-04-x64",
        ip_address="192.168.1.100",
        tags=["minecraft-tui", "minecraft-server"],
    )

    assert droplet.id == 12345
    assert droplet.name == "minecraft-server"
    assert droplet.status == "active"
    assert droplet.ip_address == "192.168.1.100"
    assert "minecraft-tui" in droplet.tags


def test_droplet_create_request():
    """Test droplet creation request model."""
    request = DropletCreateRequest(
        name="test-server",
        region="nyc3",
        size="s-2vcpu-4gb",
        image="ubuntu-24-04-x64",
        ssh_keys=[123],
    )

    assert request.name == "test-server"
    assert request.region == "nyc3"
    assert request.monitoring is True
    assert request.ipv6 is True
    assert "minecraft-tui" in request.tags
