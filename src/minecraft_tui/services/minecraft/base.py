"""Base Minecraft server installer."""

import asyncio
import contextlib
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

    # Path to installation log on the server
    INSTALL_LOG_PATH = "/opt/minecraft/install.log"

    def __init__(self, config: ServerConfig):
        self.config = config
        self.ssh_client: paramiko.SSHClient | None = None

    async def connect_ssh(
        self,
        host: str,
        username: str = "root",
        key_path: str | None = None,
        max_retries: int = 12,
        initial_delay: int = 5,
        progress_callback: Callable[[str], None] | None = None,
    ):
        """Establish SSH connection to droplet with retry logic.

        Args:
            host: Droplet IP address
            username: SSH username
            key_path: Path to SSH private key
            max_retries: Maximum number of retry attempts (default: 12)
            initial_delay: Initial delay in seconds between retries (default: 5)
            progress_callback: Optional callback for progress updates

        Raises:
            SSHError: If connection fails after all retries
        """
        last_error = None

        for attempt in range(max_retries):
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
                if progress_callback:
                    progress_callback(f"✓ SSH connection established to {host}")
                return
            except Exception as e:
                last_error = e
                # Clean up failed client
                if self.ssh_client:
                    with contextlib.suppress(Exception):
                        self.ssh_client.close()
                    self.ssh_client = None

                # Last attempt - don't retry
                if attempt == max_retries - 1:
                    break

                # Calculate exponential backoff delay
                delay = initial_delay * (2**attempt)
                if progress_callback:
                    progress_callback(
                        f"SSH connection failed (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay} seconds..."
                    )

                await asyncio.sleep(delay)

        raise SSHError(
            f"Failed to connect to {host} after {max_retries} attempts: {last_error}"
        ) from last_error

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
                # Truncate command for display if too long
                cmd_display = command[:100] + "..." if len(command) > 100 else command
                error_msg = f"Command failed with exit code {exit_status}"
                error_msg += f"\n  Command: {cmd_display}"
                if stderr_output:
                    # Limit stderr to last 500 chars
                    stderr_display = (
                        stderr_output[-500:] if len(stderr_output) > 500 else stderr_output
                    )
                    error_msg += f"\n  Error: {stderr_display.strip()}"
                if output_lines:
                    # Show last 5 lines of stdout for context
                    last_lines = output_lines[-5:]
                    error_msg += f"\n  Last output: {' | '.join(last_lines)}"
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

    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Callable[[str], None] | None = None,
    ):
        """Upload a local file to the remote server via SFTP.

        Args:
            local_path: Path to local file
            remote_path: Destination path on remote server
            progress_callback: Optional callback for progress updates

        Raises:
            SSHError: If upload fails
        """
        import os
        from pathlib import Path

        if self.ssh_client is None:
            raise SSHError("Not connected to SSH server")

        # Expand user path (e.g., ~/Downloads -> /home/user/Downloads)
        local_path = str(Path(local_path).expanduser())

        if not os.path.exists(local_path):
            raise SSHError(f"Local file not found: {local_path}")

        file_size = os.path.getsize(local_path)
        file_size_mb = file_size / (1024 * 1024)

        if progress_callback:
            progress_callback(f"Uploading {Path(local_path).name} ({file_size_mb:.1f} MB)...")

        def _upload():
            """Blocking function to upload file via SFTP."""
            sftp = self.ssh_client.open_sftp()
            try:
                sftp.put(local_path, remote_path)
            finally:
                sftp.close()

        try:
            await asyncio.to_thread(_upload)
            if progress_callback:
                progress_callback(f"✓ Upload complete: {remote_path}")
        except Exception as e:
            raise SSHError(f"Failed to upload file: {e}") from e

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

    async def init_install_log(self, progress_callback: Callable[[str], None] | None = None):
        """Initialize the installation log file on the server.

        Args:
            progress_callback: Optional callback for progress updates
        """
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        header = f"""# Minecraft Server Installation Log
# Server: {self.config.name}
# Type: {self.config.server_type.value}
# Minecraft Version: {self.config.minecraft_version}
# Started: {timestamp}
# ================================================

"""
        # Create the log file with header
        await self.execute_command(
            f"mkdir -p /opt/minecraft && cat > {self.INSTALL_LOG_PATH} << 'LOGEOF'\n{header}LOGEOF",
            None,  # Don't stream this to progress
        )
        if progress_callback:
            progress_callback(f"Installation log: {self.INSTALL_LOG_PATH}")

    async def log_to_file(self, message: str):
        """Append a message to the installation log file on the server.

        Args:
            message: Message to log
        """
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        # Escape message for shell
        safe_message = message.replace("'", "'\\''").replace("\n", " ")
        await self.execute_command(
            f"echo '[{timestamp}] {safe_message}' >> {self.INSTALL_LOG_PATH}",
            None,  # Don't stream this to progress
        )

    async def finalize_install_log(self, success: bool, error_message: str | None = None):
        """Finalize the installation log with completion status.

        Args:
            success: Whether installation succeeded
            error_message: Error message if failed
        """
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        if success:
            footer = f"""
# ================================================
# Installation completed successfully
# Finished: {timestamp}
# ================================================
"""
        else:
            safe_error = (error_message or "Unknown error").replace("'", "'\\''")
            footer = f"""
# ================================================
# Installation FAILED
# Error: {safe_error}
# Finished: {timestamp}
# ================================================
"""
        await self.execute_command(
            f"cat >> {self.INSTALL_LOG_PATH} << 'LOGEOF'\n{footer}LOGEOF",
            None,
        )

    def wrap_progress_callback(
        self, progress_callback: Callable[[str], None] | None
    ) -> Callable[[str], None]:
        """Create a wrapped progress callback that logs to both UI and file.

        This returns a synchronous callback that queues log writes.
        The actual file logging happens asynchronously.

        Args:
            progress_callback: Original progress callback (or None)

        Returns:
            Wrapped callback that logs to both destinations
        """
        log_queue: list[str] = []

        def wrapped_callback(message: str) -> None:
            # Call original callback if provided
            if progress_callback:
                progress_callback(message)
            # Queue message for file logging
            log_queue.append(message)

        # Store queue reference for later flushing
        self._log_queue = log_queue

        # Log that wrapping is set up
        if progress_callback:
            progress_callback("Installation log capture started")

        return wrapped_callback

    async def flush_log_queue(self, progress_callback: Callable[[str], None] | None = None):
        """Flush queued log messages to the installation log file.

        Args:
            progress_callback: Optional callback for progress updates
        """
        queue_size = len(self._log_queue) if hasattr(self, "_log_queue") else 0

        if progress_callback:
            progress_callback(f"Saving {queue_size} log entries to installation log...")

        if not hasattr(self, "_log_queue") or not self._log_queue:
            # Still write a message even if queue is empty
            if progress_callback:
                progress_callback("No additional log entries to save")
            return

        from datetime import datetime

        # Build all log lines at once
        lines = []
        for message in self._log_queue:
            timestamp = datetime.now().strftime("%H:%M:%S")
            # Escape for shell heredoc - be more thorough
            safe_message = message.replace("\\", "\\\\").replace("'", "'\\''").replace("\n", " ")
            lines.append(f"[{timestamp}] {safe_message}")

        # Write all lines in one command using heredoc
        if lines:
            content = "\n".join(lines)
            await self.execute_command(
                f"cat >> {self.INSTALL_LOG_PATH} << 'LOGEOF'\n{content}\nLOGEOF",
                None,
            )
            if progress_callback:
                progress_callback(f"Wrote {len(lines)} log entries to installation log")

        self._log_queue.clear()
