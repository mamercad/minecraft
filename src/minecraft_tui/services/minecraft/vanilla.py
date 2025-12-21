# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""Vanilla Minecraft server installer."""

from collections.abc import Callable

import aiohttp

from .base import BaseMinecraftInstaller, InstallationError


class VanillaInstaller(BaseMinecraftInstaller):
    """Installer for vanilla Minecraft servers."""

    async def get_server_jar_url(self) -> str:
        """Fetch the download URL for the specified Minecraft version.

        Returns:
            Server JAR download URL

        Raises:
            InstallationError: If version manifest fetch fails
        """
        version = self.config.minecraft_version

        try:
            # Fetch version manifest
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://launchermeta.mojang.com/mc/game/version_manifest.json"
                ) as resp:
                    manifest = await resp.json()

                # Find the specified version
                for version_info in manifest["versions"]:
                    if version_info["id"] == version:
                        # Fetch version-specific manifest
                        async with session.get(version_info["url"]) as version_resp:
                            version_data = await version_resp.json()
                            return version_data["downloads"]["server"]["url"]

                raise InstallationError(f"Minecraft version {version} not found")
        except Exception as e:
            raise InstallationError(f"Failed to fetch server JAR URL: {e}") from e

    async def install(self, progress_callback: Callable[[str], None] | None = None):
        """Install vanilla Minecraft server.

        Args:
            progress_callback: Optional callback for installation progress

        Raises:
            InstallationError: If installation fails
        """
        try:
            if progress_callback:
                progress_callback("=" * 50)
                progress_callback("VANILLA SERVER INSTALLATION")
                progress_callback(f"Minecraft Version: {self.config.minecraft_version}")
                progress_callback(f"Server Name: {self.config.name}")
                progress_callback(f"Memory: {self.config.memory_mb}MB")
                progress_callback("=" * 50)

            # 0. Wait for cloud-init to complete
            await self.wait_for_cloud_init(progress_callback)

            # 1. Install Java
            if progress_callback:
                progress_callback("[1/9] Installing Java 21 (OpenJDK JRE)...")
            await self.execute_apt_with_retry(
                "DEBIAN_FRONTEND=noninteractive apt-get update && "
                "DEBIAN_FRONTEND=noninteractive apt-get install -y openjdk-21-jre-headless",
                progress_callback,
            )

            # Verify Java installation
            if progress_callback:
                progress_callback("Verifying Java installation...")
            stdout, _ = await self.execute_command("java -version 2>&1 | head -1", None)
            if progress_callback:
                progress_callback(f"Java: {stdout.strip()}")

            # 2. Create minecraft user and group
            if progress_callback:
                progress_callback("[2/9] Creating minecraft user...")
            await self.execute_command(
                "useradd -r -m -d /opt/minecraft -s /bin/bash minecraft || true",
                progress_callback,
            )

            # 3. Create server directory
            if progress_callback:
                progress_callback("[3/9] Creating server directory /opt/minecraft...")
            await self.execute_command("mkdir -p /opt/minecraft", progress_callback)

            # 4. Download server jar
            if progress_callback:
                progress_callback(f"[4/9] Fetching Minecraft {self.config.minecraft_version} download URL...")
            jar_url = await self.get_server_jar_url()
            if progress_callback:
                progress_callback(f"Download URL: {jar_url}")
                progress_callback("Downloading server.jar...")
            await self.execute_command(
                f"wget -q -O /opt/minecraft/server.jar '{jar_url}'", progress_callback
            )

            # Verify download
            stdout, _ = await self.execute_command(
                "ls -lh /opt/minecraft/server.jar | awk '{print $5}'", None
            )
            if progress_callback:
                progress_callback(f"Downloaded server.jar: {stdout.strip()}")

            # 5. Create eula.txt
            if progress_callback:
                progress_callback("[5/9] Creating EULA (eula=true)...")
            eula_content = self.create_eula_txt()
            await self.execute_command(
                f"echo '{eula_content}' > /opt/minecraft/eula.txt", progress_callback
            )

            # 6. Create server.properties
            if progress_callback:
                progress_callback("[6/9] Writing server.properties...")
            props_content = self.escape_for_shell(self.create_server_properties())
            await self.execute_command(
                f"cat > /opt/minecraft/server.properties << 'EOF'\n{props_content}\nEOF",
                progress_callback,
            )

            # 7. Set ownership
            if progress_callback:
                progress_callback("[7/9] Setting file ownership to minecraft:minecraft...")
            await self.execute_command(
                "chown -R minecraft:minecraft /opt/minecraft", progress_callback
            )

            # 8. Create systemd service
            if progress_callback:
                progress_callback("[8/9] Creating systemd service 'minecraft'...")
            service_content = self._create_systemd_service()
            await self.execute_command(
                f"cat > /etc/systemd/system/minecraft.service << 'EOF'\n{service_content}\nEOF",
                progress_callback,
            )
            if progress_callback:
                progress_callback(f"Service command: java -Xmx{self.config.memory_mb}M -jar server.jar nogui")

            # 9. Start server
            if progress_callback:
                progress_callback("[9/9] Starting Minecraft server...")
            await self.execute_command("systemctl daemon-reload", progress_callback)
            await self.execute_command("systemctl enable minecraft", progress_callback)
            await self.execute_command("systemctl start minecraft", progress_callback)

            # Verify service started
            stdout, _ = await self.execute_command("systemctl is-active minecraft", None)
            if progress_callback:
                progress_callback(f"Service status: {stdout.strip()}")
                progress_callback("=" * 50)
                progress_callback("VANILLA SERVER INSTALLATION COMPLETE")
                progress_callback("=" * 50)

        except Exception as e:
            raise InstallationError(f"Vanilla server installation failed: {e}") from e

    def _create_systemd_service(self) -> str:
        """Generate systemd service file.

        Returns:
            Systemd service file content
        """
        return f"""[Unit]
Description=Minecraft Server
After=network.target

[Service]
Type=simple
User=minecraft
Group=minecraft
WorkingDirectory=/opt/minecraft
ExecStart=/usr/bin/java -Xmx{self.config.memory_mb}M -Xms{self.config.memory_mb}M -jar server.jar nogui
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
