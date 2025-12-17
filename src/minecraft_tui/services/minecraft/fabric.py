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
            # 0. Wait for cloud-init to complete
            await self.wait_for_cloud_init(progress_callback)

            # 1. Install Java
            if progress_callback:
                progress_callback("Installing Java 21...")
            await self.execute_apt_with_retry(
                "DEBIAN_FRONTEND=noninteractive apt-get update && "
                "DEBIAN_FRONTEND=noninteractive apt-get install -y openjdk-21-jre-headless",
                progress_callback,
            )

            # 2. Create minecraft user and group
            if progress_callback:
                progress_callback("Creating minecraft user...")
            await self.execute_command(
                "useradd -r -m -d /opt/minecraft -s /bin/bash minecraft || true",
                progress_callback,
            )

            # 3. Create server directory
            if progress_callback:
                progress_callback("Creating server directory...")
            await self.execute_command("mkdir -p /opt/minecraft", progress_callback)

            # 4. Get Fabric loader version
            fabric_version = self.config.fabric_version
            if not fabric_version or fabric_version == "latest":
                if progress_callback:
                    progress_callback("Fetching latest Fabric loader version...")
                fabric_version = await self.get_latest_loader_version()
                if progress_callback:
                    progress_callback(f"Using Fabric loader version: {fabric_version}")

            # 5. Download Fabric server JAR
            if progress_callback:
                progress_callback("Downloading Fabric server...")
            mc_version = self.config.minecraft_version
            server_url = f"https://meta.fabricmc.net/v2/versions/loader/{mc_version}/{fabric_version}/1.0.1/server/jar"
            await self.execute_command(
                f"wget -q -O /opt/minecraft/server.jar '{server_url}'",
                progress_callback,
            )

            # 6. Create eula.txt
            if progress_callback:
                progress_callback("Creating EULA...")
            eula_content = self.create_eula_txt()
            await self.execute_command(
                f"echo '{eula_content}' > /opt/minecraft/eula.txt", progress_callback
            )

            # 7. Create server.properties
            if progress_callback:
                progress_callback("Configuring server...")
            props_content = self.escape_for_shell(self.create_server_properties())
            await self.execute_command(
                f"cat > /opt/minecraft/server.properties << 'EOF'\n{props_content}\nEOF",
                progress_callback,
            )

            # 8. Set ownership
            if progress_callback:
                progress_callback("Setting permissions...")
            await self.execute_command(
                "chown -R minecraft:minecraft /opt/minecraft", progress_callback
            )

            # 9. Create systemd service
            if progress_callback:
                progress_callback("Creating systemd service...")
            service_content = self._create_systemd_service()
            await self.execute_command(
                f"cat > /etc/systemd/system/minecraft.service << 'EOF'\n{service_content}\nEOF",
                progress_callback,
            )

            # 10. Start server
            if progress_callback:
                progress_callback("Starting server...")
            await self.execute_command("systemctl daemon-reload", progress_callback)
            await self.execute_command("systemctl enable minecraft", progress_callback)
            await self.execute_command("systemctl start minecraft", progress_callback)

            if progress_callback:
                progress_callback("Installation complete!")

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
ExecStart=/usr/bin/java -Xmx{self.config.memory_mb}M -Xms{self.config.memory_mb}M -jar server.jar nogui
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
