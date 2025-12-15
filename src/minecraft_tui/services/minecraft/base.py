"""Base Minecraft server installer."""

from abc import ABC, abstractmethod
from collections.abc import Callable

import paramiko

from ...models.server import ServerConfig


class InstallationError(Exception):
    """Base exception for installation errors."""

    pass


class SSHError(InstallationError):
    """SSH connection or execution errors."""

    pass


class BaseMinecraftInstaller(ABC):
    """Base class for Minecraft server installers."""

    def __init__(self, config: ServerConfig):
        self.config = config
        self.ssh_client: paramiko.SSHClient | None = None

    def connect_ssh(self, host: str, username: str = "root", key_path: str | None = None):
        """Establish SSH connection to droplet.

        Args:
            host: Droplet IP address
            username: SSH username
            key_path: Path to SSH private key

        Raises:
            SSHError: If connection fails
        """
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                hostname=host,
                username=username,
                key_filename=key_path,
                timeout=30,
            )
        except Exception as e:
            raise SSHError(f"Failed to connect to {host}: {e}") from e

    def execute_command(
        self, command: str, progress_callback: Callable[[str], None] | None = None
    ) -> tuple[str, str]:
        """Execute command via SSH and stream output.

        Args:
            command: Shell command to execute
            progress_callback: Optional callback for streaming output

        Returns:
            Tuple of (stdout, stderr)

        Raises:
            SSHError: If command execution fails
        """
        if self.ssh_client is None:
            raise SSHError("Not connected to SSH server")

        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)

            output_lines = []
            for line in stdout:
                line = line.strip()
                output_lines.append(line)
                if progress_callback:
                    progress_callback(line)

            return "\n".join(output_lines), stderr.read().decode()
        except Exception as e:
            raise SSHError(f"Failed to execute command: {e}") from e

    def disconnect(self):
        """Close SSH connection."""
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None

    @abstractmethod
    async def install(self, progress_callback: Callable[[str], None] | None = None):
        """Install the Minecraft server - must be implemented by subclasses.

        Args:
            progress_callback: Optional callback for installation progress

        Raises:
            InstallationError: If installation fails
        """
        pass

    def create_server_properties(self) -> str:
        """Generate server.properties file content.

        Returns:
            server.properties file content
        """
        props = [
            f"max-players={self.config.max_players}",
            f"server-port={self.config.server_port}",
            "online-mode=true",
            "white-list=false",
        ]

        for key, value in self.config.server_properties.items():
            props.append(f"{key}={str(value).lower()}")

        return "\n".join(props)

    def create_eula_txt(self) -> str:
        """Generate eula.txt content.

        Returns:
            eula.txt file content
        """
        return f"eula={str(self.config.accept_eula).lower()}"

    def escape_for_shell(self, content: str) -> str:
        """Escape content for safe shell usage in heredoc.

        Args:
            content: Content to escape

        Returns:
            Escaped content
        """
        return content.replace("'", "'\\''")
