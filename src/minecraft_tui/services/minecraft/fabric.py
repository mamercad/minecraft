# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""Fabric Minecraft server installer."""

from collections.abc import Callable

import aiohttp

from .base import BaseMinecraftInstaller, InstallationError


class FabricInstaller(BaseMinecraftInstaller):
    """Installer for Fabric Minecraft servers."""

    async def get_fabric_installer_url(self) -> str:
        """Get Fabric installer URL.

        Returns:
            Fabric installer download URL
        """
        # Use the official Fabric installer JAR
        return "https://meta.fabricmc.net/v2/versions/loader/{mc_version}/{loader_version}/1.0.1/server/jar"

    async def get_latest_loader_version(self) -> str:
        """Fetch the latest stable Fabric loader version.

        Returns:
            Latest Fabric loader version

        Raises:
            InstallationError: If version fetch fails
        """
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get("https://meta.fabricmc.net/v2/versions/loader") as resp,
            ):
                versions = await resp.json()
                if versions and len(versions) > 0:
                    # Get the latest stable version
                    return versions[0]["version"]
                raise InstallationError("No Fabric loader versions found")
        except Exception as e:
            raise InstallationError(f"Failed to fetch Fabric loader version: {e}") from e

    async def install(self, progress_callback: Callable[[str], None] | None = None):
        """Install Fabric Minecraft server.

        Args:
            progress_callback: Optional callback for installation progress

        Raises:
            InstallationError: If installation fails
        """
        try:
            # Get Fabric loader version early for logging
            fabric_version = self.config.fabric_version
            if not fabric_version or fabric_version == "latest":
                fabric_version = await self.get_latest_loader_version()

            if progress_callback:
                progress_callback("=" * 50)
                progress_callback("FABRIC SERVER INSTALLATION")
                progress_callback(f"Minecraft Version: {self.config.minecraft_version}")
                progress_callback(f"Fabric Loader: {fabric_version}")
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

            # 4. Download Fabric server JAR (bundled with Minecraft)
            mc_version = self.config.minecraft_version
            server_url = f"https://meta.fabricmc.net/v2/versions/loader/{mc_version}/{fabric_version}/1.0.1/server/jar"

            if progress_callback:
                progress_callback(f"[4/9] Downloading Fabric server JAR...")
                progress_callback(f"Minecraft: {mc_version}")
                progress_callback(f"Fabric Loader: {fabric_version}")
                progress_callback(f"URL: {server_url}")

            await self.execute_command(
                f"wget -q -O /opt/minecraft/server.jar '{server_url}'",
                progress_callback,
            )

            # Verify download - Fabric JAR should be larger than vanilla (~10MB+ vs ~50MB vanilla inside)
            stdout, _ = await self.execute_command(
                "ls -lh /opt/minecraft/server.jar | awk '{print $5}'", None
            )
            if progress_callback:
                progress_callback(f"Downloaded server.jar: {stdout.strip()}")
                progress_callback("(Fabric server JAR includes Minecraft + Fabric loader)")

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
                progress_callback(f"Service command: java -Xmx{self.config.memory_mb}M -jar server.jar")

            # 9. Start server
            if progress_callback:
                progress_callback("[9/9] Starting Fabric Minecraft server...")
            await self.execute_command("systemctl daemon-reload", progress_callback)
            await self.execute_command("systemctl enable minecraft", progress_callback)
            await self.execute_command("systemctl start minecraft", progress_callback)

            # Verify service started
            stdout, _ = await self.execute_command("systemctl is-active minecraft", None)
            if progress_callback:
                progress_callback(f"Service status: {stdout.strip()}")

            # Show mods directory info
            if progress_callback:
                progress_callback("")
                progress_callback("NOTE: Fabric is installed but no mods are included.")
                progress_callback("To add mods, upload .jar files to /opt/minecraft/mods/")
                progress_callback("Then restart: systemctl restart minecraft")
                progress_callback("")
                progress_callback("=" * 50)
                progress_callback("FABRIC SERVER INSTALLATION COMPLETE")
                progress_callback("=" * 50)

        except Exception as e:
            raise InstallationError(f"Fabric server installation failed: {e}") from e

    def _create_systemd_service(self) -> str:
        """Generate systemd service file for Fabric.

        Returns:
            Systemd service file content
        """
        return f"""[Unit]
Description=Minecraft Fabric Server
After=network.target

[Service]
Type=simple
User=minecraft
Group=minecraft
WorkingDirectory=/opt/minecraft
ExecStart=/usr/bin/java -Xmx{self.config.memory_mb}M -Xms{self.config.memory_mb}M -jar server.jar
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
