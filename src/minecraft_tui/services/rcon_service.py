"""RCON service for Minecraft server management."""

import asyncio
import contextlib
import struct
import sys
from pathlib import Path

import paramiko

# Debug logging to file
DEBUG_LOG = Path("/tmp/minecraft_tui_rcon_debug.log")

def debug_log(msg: str):
    """Write debug message to log file."""
    with open(DEBUG_LOG, "a") as f:
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        f.write(f"[{timestamp}] {msg}\n")
        f.flush()


class RconError(Exception):
    """Base exception for RCON operations."""

    pass


class RconService:
    """Service for RCON operations with Minecraft servers."""

    # RCON packet types
    SERVERDATA_AUTH = 3
    SERVERDATA_AUTH_RESPONSE = 2
    SERVERDATA_EXECCOMMAND = 2
    SERVERDATA_RESPONSE_VALUE = 0

    def __init__(self, host: str, port: int = 25575):
        self.host = host
        self.port = port
        self.password: str | None = None
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.request_id = 0

    async def get_rcon_password_from_server(self, ssh_key_path: str) -> str:
        """Retrieve RCON password from server.properties via SSH.

        Args:
            ssh_key_path: Path to SSH private key

        Returns:
            RCON password from server.properties

        Raises:
            RconError: If password retrieval fails
        """
        try:
            # Run in thread pool since paramiko is blocking
            return await asyncio.to_thread(self._get_password_via_ssh, ssh_key_path)
        except Exception as e:
            raise RconError(f"Failed to retrieve RCON password: {e}") from e

    def _get_password_via_ssh(self, ssh_key_path: str) -> str:
        """Get RCON password via SSH (blocking operation).

        Args:
            ssh_key_path: Path to SSH private key

        Returns:
            RCON password

        Raises:
            RconError: If retrieval fails
        """
        ssh_client = None
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(
                hostname=self.host,
                username="root",
                key_filename=ssh_key_path,
                timeout=10,
            )

            # First check if server.properties exists
            stdin, stdout, stderr = ssh_client.exec_command(
                "test -f /opt/minecraft/server.properties && echo 'exists' || echo 'missing'"
            )
            file_check = stdout.read().decode().strip()

            if file_check == "missing":
                raise RconError(
                    "server.properties not found at /opt/minecraft/server.properties. "
                    "The Minecraft server may not be fully installed yet."
                )

            # Check if RCON is enabled
            stdin, stdout, stderr = ssh_client.exec_command(
                "grep '^enable-rcon=' /opt/minecraft/server.properties | cut -d'=' -f2"
            )
            rcon_enabled = stdout.read().decode().strip()

            if rcon_enabled != "true":
                raise RconError(
                    f"RCON is not enabled (enable-rcon={rcon_enabled or 'not set'}). "
                    "This server may have been created before RCON support was added."
                )

            # Read RCON password from server.properties
            stdin, stdout, stderr = ssh_client.exec_command(
                "grep '^rcon.password=' /opt/minecraft/server.properties | cut -d'=' -f2"
            )
            password = stdout.read().decode().strip()

            if not password:
                raise RconError(
                    "RCON password not found in server.properties. "
                    "This server may need to be recreated with RCON support."
                )

            return password

        except RconError:
            raise
        except Exception as e:
            raise RconError(f"SSH connection failed: {e}") from e
        finally:
            if ssh_client:
                ssh_client.close()

    def _pack_packet(self, packet_type: int, payload: str) -> bytes:
        """Pack RCON packet.

        Args:
            packet_type: Type of packet
            payload: Payload string

        Returns:
            Packed packet bytes
        """
        self.request_id += 1
        payload_bytes = payload.encode("utf-8") + b"\x00\x00"
        packet_size = len(payload_bytes) + 8  # 4 (ID) + 4 (Type)

        return (
            struct.pack("<i", packet_size)
            + struct.pack("<ii", self.request_id, packet_type)
            + payload_bytes
        )

    async def _read_packet(self) -> tuple[int, int, bytes]:
        """Read RCON packet from server.

        Returns:
            Tuple of (request_id, packet_type, payload)

        Raises:
            RconError: If read fails
        """
        debug_log("_read_packet() called")
        if not self.reader:
            raise RconError("Not connected to RCON server")

        try:
            # Read packet size
            debug_log("Reading 4 bytes for packet size...")
            size_data = await self.reader.readexactly(4)
            debug_log(f"Got size_data: {size_data.hex()}")
            size = struct.unpack("<i", size_data)[0]
            debug_log(f"Packet size: {size} bytes")

            # Read packet data
            debug_log(f"Reading {size} bytes for packet data...")
            packet_data = await self.reader.readexactly(size)
            debug_log(f"Got packet_data: {len(packet_data)} bytes")
            request_id, packet_type = struct.unpack("<ii", packet_data[:8])
            payload = packet_data[8:-2]  # Remove trailing null bytes
            debug_log(f"Decoded: req_id={request_id}, type={packet_type}, payload_len={len(payload)}")

            return request_id, packet_type, payload
        except Exception as e:
            debug_log(f"Exception in _read_packet: {type(e).__name__}: {e}")
            raise RconError(f"Failed to read packet: {e}") from e

    async def connect(self, password: str) -> None:
        """Connect to RCON server.

        Args:
            password: RCON password

        Raises:
            RconError: If connection fails
        """
        debug_log(f"RconService.connect() called")
        debug_log(f"Host: {self.host}, Port: {self.port}")
        debug_log(f"Password: {password} (len={len(password)})")

        self.password = password
        try:
            # Open TCP connection with timeout
            try:
                debug_log(f"Opening TCP connection to {self.host}:{self.port}...")
                self.reader, self.writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port), timeout=10.0
                )
                debug_log(f"TCP connection established!")
            except ConnectionRefusedError as e:
                raise RconError(
                    f"Connection refused to {self.host}:{self.port}. "
                    f"RCON port is not listening or server is not running. "
                    f"Check: systemctl status minecraft"
                ) from e
            except OSError as e:
                if e.errno == 61:  # ECONNREFUSED on macOS
                    raise RconError(
                        f"Connection refused to {self.host}:{self.port}. "
                        f"RCON is not listening. Verify rcon.address=0.0.0.0 in server.properties"
                    ) from e
                raise RconError(f"Network error connecting to {self.host}:{self.port}: {e}") from e

            # Send authentication packet
            auth_packet = self._pack_packet(self.SERVERDATA_AUTH, password)
            debug_log(f"Sending auth packet: {len(auth_packet)} bytes")
            debug_log(f"Password being sent: {password}")
            debug_log(f"Request ID: {self.request_id}")
            self.writer.write(auth_packet)
            await self.writer.drain()
            debug_log(f"Auth packet sent and drained")

            # Wait for server to process (Minecraft can be slow)
            await asyncio.sleep(0.5)
            debug_log(f"Waited 0.5s, now reading response...")

            # Read authentication response (with longer timeout)
            try:
                debug_log(f"Calling _read_packet() with 15s timeout...")
                req_id, packet_type, _ = await asyncio.wait_for(
                    self._read_packet(), timeout=15.0
                )
                debug_log(f"Received response: req_id={req_id}, packet_type={packet_type}")
            except asyncio.TimeoutError as e:
                raise RconError(
                    "Server did not respond to authentication request after 15 seconds. "
                    "Possible causes: (1) RCON password mismatch - server silently drops connection, "
                    "(2) Server is processing too slowly, (3) RCON protocol version mismatch. "
                    f"Check server logs with: ssh root@{self.host} 'tail -50 /opt/minecraft/logs/latest.log'"
                ) from e
            except (ConnectionResetError, BrokenPipeError) as e:
                raise RconError(
                    "Connection closed by server during authentication. "
                    "This usually means the RCON password is incorrect or the authentication packet is malformed."
                ) from e
            except asyncio.IncompleteReadError as e:
                raise RconError(
                    "Server closed connection before sending authentication response. "
                    "Check if RCON is properly configured in server.properties."
                ) from e

            # Read the second response packet (RCON sends two responses for auth)
            try:
                await asyncio.wait_for(self._read_packet(), timeout=5.0)
            except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError, asyncio.TimeoutError):
                # Sometimes server only sends one packet, that's ok if first packet succeeded
                debug_log("Second packet not received (this is OK)")
                pass

            # Check authentication (req_id of -1 means auth failed)
            if req_id == -1:
                raise RconError(
                    "Authentication failed - RCON password is incorrect. "
                    "The password in server.properties doesn't match."
                )

        except asyncio.TimeoutError as e:
            raise RconError(
                f"Connection timeout. Server may be overloaded or network issues. Try again."
            ) from e
        except RconError:
            raise
        except Exception as e:
            raise RconError(f"Unexpected error during RCON connection: {e}") from e

    async def send_command(self, command: str) -> str:
        """Send command to Minecraft server via RCON.

        Args:
            command: Minecraft command to execute

        Returns:
            Server response

        Raises:
            RconError: If command fails
        """
        if not self.writer or not self.reader:
            raise RconError("Not connected to RCON server")

        try:
            # Send command packet
            cmd_packet = self._pack_packet(self.SERVERDATA_EXECCOMMAND, command)
            self.writer.write(cmd_packet)
            await self.writer.drain()

            # Read response
            _, _, payload = await self._read_packet()

            return payload.decode("utf-8")
        except RconError:
            raise
        except Exception as e:
            raise RconError(f"Command failed: {e}") from e

    async def get_server_logs(self, ssh_key_path: str, lines: int = 100) -> list[str]:
        """Get recent server logs via SSH.

        Args:
            ssh_key_path: Path to SSH private key
            lines: Number of log lines to retrieve

        Returns:
            List of log lines

        Raises:
            RconError: If log retrieval fails
        """
        try:
            return await asyncio.to_thread(self._get_logs_via_ssh, ssh_key_path, lines)
        except Exception as e:
            raise RconError(f"Failed to retrieve logs: {e}") from e

    def _get_logs_via_ssh(self, ssh_key_path: str, lines: int) -> list[str]:
        """Get logs via SSH (blocking operation).

        Args:
            ssh_key_path: Path to SSH private key
            lines: Number of lines

        Returns:
            List of log lines
        """
        ssh_client = None
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(
                hostname=self.host,
                username="root",
                key_filename=ssh_key_path,
                timeout=10,
            )

            # Get logs from Minecraft's log file
            stdin, stdout, stderr = ssh_client.exec_command(
                f"tail -n {lines} /opt/minecraft/logs/latest.log 2>/dev/null || echo 'No log file found'"
            )
            output = stdout.read().decode()

            return output.split("\n")

        except Exception as e:
            raise RconError(f"Log retrieval failed: {e}") from e
        finally:
            if ssh_client:
                ssh_client.close()

    def disconnect(self) -> None:
        """Disconnect from RCON server."""
        if self.writer:
            with contextlib.suppress(Exception):
                self.writer.close()
            self.writer = None
            self.reader = None
