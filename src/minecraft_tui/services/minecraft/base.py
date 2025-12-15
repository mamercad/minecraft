"""Base Minecraft server installer."""

import asyncio
import time
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

    async def connect_ssh(self, host: str, username: str = "root", key_path: str | None = None):
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
            # Wrap blocking connect call with asyncio.to_thread
            await asyncio.to_thread(
                self.ssh_client.connect,
                hostname=host,
                username=username,
                key_filename=key_path,
                timeout=30,
            )
        except Exception as e:
            raise SSHError(f"Failed to connect to {host}: {e}") from e

    async def execute_command(
        self, command: str, progress_callback: Callable[[str], None] | None = None
    ) -> tuple[str, str]:
        """Execute command via SSH and stream output.

        Args:
            command: Shell command to execute
            progress_callback: Optional callback for streaming output

        Returns:
            Tuple of (stdout, stderr)

        Raises:
            SSHError: If command execution fails or returns non-zero exit code
        """
        if self.ssh_client is None:
            raise SSHError("Not connected to SSH server")

        def _execute():
            """Blocking function to execute SSH command and stream output."""
            stdin, stdout, stderr = self.ssh_client.exec_command(command)

            output_lines = []
            for line in stdout:
                line = line.strip()
                output_lines.append(line)
                if progress_callback:
                    progress_callback(line)

            stderr_output = stderr.read().decode()
            exit_status = stdout.channel.recv_exit_status()

            # Check if command failed
            if exit_status != 0:
                error_msg = f"Command failed with exit code {exit_status}"
                if stderr_output:
                    error_msg += f": {stderr_output}"
                raise SSHError(error_msg)

            return "\n".join(output_lines), stderr_output

        try:
            # Wrap blocking SSH execution with asyncio.to_thread
            return await asyncio.to_thread(_execute)
        except SSHError:
            raise
        except Exception as e:
            raise SSHError(f"Failed to execute command: {e}") from e

    def disconnect(self):
        """Close SSH connection."""
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None

    async def wait_for_cloud_init(
        self, progress_callback: Callable[[str], None] | None = None, timeout: int = 300
    ):
        """Wait for cloud-init to complete before proceeding.

        Args:
            progress_callback: Optional callback for progress updates
            timeout: Maximum time to wait in seconds (default: 300)

        Raises:
            SSHError: If timeout is reached or command fails
        """
        if progress_callback:
            progress_callback("Waiting for cloud-init to complete...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if cloud-init is done
                stdout, _ = await self.execute_command("cloud-init status --wait", None)
                if "done" in stdout.lower():
                    if progress_callback:
                        progress_callback("Cloud-init completed successfully")
                    return
            except SSHError:
                # cloud-init might not be done yet, keep waiting
                pass

            await asyncio.sleep(5)

        raise SSHError(f"Timeout waiting for cloud-init to complete after {timeout} seconds")

    async def execute_apt_with_retry(
        self,
        command: str,
        progress_callback: Callable[[str], None] | None = None,
        max_retries: int = 10,
        initial_delay: int = 10,
    ) -> tuple[str, str]:
        """Execute apt command with exponential backoff retry logic.

        Args:
            command: APT command to execute
            progress_callback: Optional callback for streaming output
            max_retries: Maximum number of retry attempts (default: 10)
            initial_delay: Initial delay in seconds between retries (default: 10)

        Returns:
            Tuple of (stdout, stderr)

        Raises:
            SSHError: If all retries are exhausted
        """
        for attempt in range(max_retries):
            try:
                return await self.execute_command(command, progress_callback)
            except SSHError as e:
                # Check if it's a lock error
                error_msg = str(e).lower()
                is_lock_error = any(
                    msg in error_msg
                    for msg in [
                        "unable to lock",
                        "could not get lock",
                        "dpkg frontend lock",
                        "apt lists lock",
                        "/var/lib/dpkg/lock",
                        "/var/lib/apt/lists/lock",
                    ]
                )

                if not is_lock_error or attempt == max_retries - 1:
                    # Not a lock error or last attempt - raise
                    raise

                # Calculate exponential backoff delay
                delay = initial_delay * (2**attempt)
                if progress_callback:
                    progress_callback(
                        f"APT is locked (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay} seconds..."
                    )

                await asyncio.sleep(delay)

        raise SSHError(f"Failed to execute apt command after {max_retries} retries")

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
