"""Forge Minecraft server installer."""

from collections.abc import Callable

from .base import BaseMinecraftInstaller, InstallationError


class ForgeInstaller(BaseMinecraftInstaller):
    """Installer for Forge Minecraft servers."""

    async def get_forge_installer_url(self) -> str:
        """Get Forge installer URL for the specified version.

        Returns:
            Forge installer download URL
        """
        mc_version = self.config.minecraft_version
        forge_version = self.config.forge_version or "latest"

        # Construct Forge installer URL
        # Format: https://maven.minecraftforge.net/net/minecraftforge/forge/{version}/forge-{version}-installer.jar
        full_version = f"{mc_version}-{forge_version}"
        return f"https://maven.minecraftforge.net/net/minecraftforge/forge/{full_version}/forge-{full_version}-installer.jar"

    async def install(self, progress_callback: Callable[[str], None] | None = None):
        """Install Forge Minecraft server.

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
                "DEBIAN_FRONTEND=noninteractive apt-get install -y openjdk-21-jre-headless openjdk-21-jdk-headless",
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

            # 4. Download Forge installer
            if progress_callback:
                progress_callback("Downloading Forge installer...")
            installer_url = await self.get_forge_installer_url()
            await self.execute_command(
                f"wget -q -O /opt/minecraft/forge-installer.jar '{installer_url}'",
                progress_callback,
            )

            # 5. Run Forge installer
            if progress_callback:
                progress_callback("Installing Forge (this may take a while)...")
            await self.execute_command(
                "cd /opt/minecraft && java -jar forge-installer.jar --installServer",
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

            # 8. Find the run script created by Forge
            if progress_callback:
                progress_callback("Configuring startup script...")

            # Make run scripts executable
            await self.execute_command(
                "cd /opt/minecraft && chmod +x run.sh 2>/dev/null || true",
                progress_callback,
            )

            # 9. Set ownership
            if progress_callback:
                progress_callback("Setting permissions...")
            await self.execute_command(
                "chown -R minecraft:minecraft /opt/minecraft", progress_callback
            )

            # 10. Create systemd service
            if progress_callback:
                progress_callback("Creating systemd service...")
            service_content = self._create_systemd_service()
            await self.execute_command(
                f"cat > /etc/systemd/system/minecraft.service << 'EOF'\n{service_content}\nEOF",
                progress_callback,
            )

            # 11. Start server
            if progress_callback:
                progress_callback("Starting server...")
            await self.execute_command("systemctl daemon-reload", progress_callback)
            await self.execute_command("systemctl enable minecraft", progress_callback)
            await self.execute_command("systemctl start minecraft", progress_callback)

            if progress_callback:
                progress_callback("Installation complete!")

        except Exception as e:
            raise InstallationError(f"Forge server installation failed: {e}") from e

    def _create_systemd_service(self) -> str:
        """Generate systemd service file for Forge.

        Returns:
            Systemd service file content
        """
        # Try to use run.sh if it exists, otherwise fallback to direct java command
        return f"""[Unit]
Description=Minecraft Forge Server
After=network.target

[Service]
Type=simple
User=minecraft
Group=minecraft
WorkingDirectory=/opt/minecraft
ExecStart=/bin/bash -c 'if [ -f run.sh ]; then ./run.sh; else java -Xmx{self.config.memory_mb}M -Xms{self.config.memory_mb}M -jar forge*.jar nogui; fi'
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
