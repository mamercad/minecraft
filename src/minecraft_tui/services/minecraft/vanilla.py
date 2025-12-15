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
            # 1. Install Java
            if progress_callback:
                progress_callback("Installing Java 21...")
            self.execute_command(
                "DEBIAN_FRONTEND=noninteractive apt-get update && "
                "DEBIAN_FRONTEND=noninteractive apt-get install -y openjdk-21-jre-headless",
                progress_callback,
            )

            # 2. Create server directory
            if progress_callback:
                progress_callback("Creating server directory...")
            self.execute_command("mkdir -p /opt/minecraft", progress_callback)

            # 3. Download server jar
            if progress_callback:
                progress_callback(f"Downloading Minecraft {self.config.minecraft_version}...")
            jar_url = await self.get_server_jar_url()
            self.execute_command(
                f"wget -q -O /opt/minecraft/server.jar '{jar_url}'", progress_callback
            )

            # 4. Create eula.txt
            if progress_callback:
                progress_callback("Creating EULA...")
            eula_content = self.create_eula_txt()
            self.execute_command(
                f"echo '{eula_content}' > /opt/minecraft/eula.txt", progress_callback
            )

            # 5. Create server.properties
            if progress_callback:
                progress_callback("Configuring server...")
            props_content = self.escape_for_shell(self.create_server_properties())
            self.execute_command(
                f"cat > /opt/minecraft/server.properties << 'EOF'\n{props_content}\nEOF",
                progress_callback,
            )

            # 6. Create systemd service
            if progress_callback:
                progress_callback("Creating systemd service...")
            service_content = self._create_systemd_service()
            self.execute_command(
                f"cat > /etc/systemd/system/minecraft.service << 'EOF'\n{service_content}\nEOF",
                progress_callback,
            )

            # 7. Start server
            if progress_callback:
                progress_callback("Starting server...")
            self.execute_command("systemctl daemon-reload", progress_callback)
            self.execute_command("systemctl enable minecraft", progress_callback)
            self.execute_command("systemctl start minecraft", progress_callback)

            if progress_callback:
                progress_callback("Installation complete!")

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
User=root
WorkingDirectory=/opt/minecraft
ExecStart=/usr/bin/java -Xmx{self.config.memory_mb}M -Xms{self.config.memory_mb}M -jar server.jar nogui
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
