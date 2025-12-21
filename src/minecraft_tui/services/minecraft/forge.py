# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""Forge Minecraft server installer."""

from collections.abc import Callable

from .base import BaseMinecraftInstaller, InstallationError
from .loader_versions import LoaderVersionService


class ForgeInstaller(BaseMinecraftInstaller):
    """Installer for Forge Minecraft servers."""

    async def get_forge_version(self) -> str:
        """Get the actual Forge version to install.

        If forge_version is None or "latest", fetches the latest version from the API.

        Returns:
            Actual Forge version number (e.g., "47.2.0")
        """
        forge_version = self.config.forge_version

        # If a specific version is set, use it
        if forge_version and forge_version != "latest":
            return forge_version

        # Otherwise, fetch the latest version from the API
        mc_version = self.config.minecraft_version
        service = LoaderVersionService()
        versions = await service.fetch_forge_versions_detailed(mc_version, limit=1)

        if versions:
            # The detailed API returns versions like "1.20.1-47.4.13"
            # We need to extract just the Forge version part
            version = versions[0]
            if version.startswith(f"{mc_version}-"):
                version = version[len(f"{mc_version}-"):]
            return version

        # Fallback: try the promotions API
        versions = await service.fetch_forge_versions(mc_version, limit=1)
        if versions:
            # Remove the "(recommended)" or "(latest)" suffix
            version = versions[0].split(" ")[0]
            return version

        raise InstallationError(
            f"Could not find any Forge versions for Minecraft {mc_version}"
        )

    async def get_forge_installer_url(self, forge_version: str) -> str:
        """Get Forge installer URL for the specified version.

        Args:
            forge_version: The Forge version number (e.g., "47.2.0")

        Returns:
            Forge installer download URL
        """
        mc_version = self.config.minecraft_version

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
            # Resolve Forge version early for logging
            forge_version = await self.get_forge_version()

            if progress_callback:
                progress_callback("=" * 50)
                progress_callback("FORGE SERVER INSTALLATION")
                progress_callback(f"Minecraft Version: {self.config.minecraft_version}")
                progress_callback(f"Forge Version: {forge_version}")
                progress_callback(f"Server Name: {self.config.name}")
                progress_callback(f"Memory: {self.config.memory_mb}MB")
                progress_callback("=" * 50)

            # 0. Wait for cloud-init to complete
            await self.wait_for_cloud_init(progress_callback)

            # 1. Install Java (Forge needs JDK for installer)
            if progress_callback:
                progress_callback("[1/11] Installing Java 21 (OpenJDK JDK + JRE)...")
                progress_callback("(Forge installer requires JDK, not just JRE)")
            await self.execute_apt_with_retry(
                "DEBIAN_FRONTEND=noninteractive apt-get update && "
                "DEBIAN_FRONTEND=noninteractive apt-get install -y openjdk-21-jre-headless openjdk-21-jdk-headless",
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
                progress_callback("[2/11] Creating minecraft user...")
            await self.execute_command(
                "useradd -r -m -d /opt/minecraft -s /bin/bash minecraft || true",
                progress_callback,
            )

            # 3. Create server directory
            if progress_callback:
                progress_callback("[3/11] Creating server directory /opt/minecraft...")
            await self.execute_command("mkdir -p /opt/minecraft", progress_callback)

            # 4. Download Forge installer
            installer_url = await self.get_forge_installer_url(forge_version)
            if progress_callback:
                progress_callback(f"[4/11] Downloading Forge installer...")
                progress_callback(f"Minecraft: {self.config.minecraft_version}")
                progress_callback(f"Forge: {forge_version}")
                progress_callback(f"URL: {installer_url}")
            try:
                await self.execute_command(
                    f"wget -O /opt/minecraft/forge-installer.jar '{installer_url}'",
                    progress_callback,
                )
            except Exception as e:
                raise InstallationError(
                    f"Failed to download Forge installer.\n"
                    f"  URL: {installer_url}\n"
                    f"  Error: {e}"
                ) from e

            # Verify download
            stdout, _ = await self.execute_command(
                "ls -lh /opt/minecraft/forge-installer.jar | awk '{print $5}'", None
            )
            if progress_callback:
                progress_callback(f"Downloaded forge-installer.jar: {stdout.strip()}")

            # 5. Run Forge installer
            if progress_callback:
                progress_callback("[5/11] Running Forge installer (this may take 2-5 minutes)...")
                progress_callback("The installer downloads Minecraft + Forge libraries...")
            await self.execute_command(
                "cd /opt/minecraft && java -jar forge-installer.jar --installServer",
                progress_callback,
            )

            # Verify installation - list installed files
            if progress_callback:
                progress_callback("Verifying Forge installation...")
            stdout, _ = await self.execute_command(
                "ls -la /opt/minecraft/*.jar 2>/dev/null | head -5", None
            )
            if progress_callback:
                for line in stdout.strip().split("\n"):
                    if line.strip():
                        progress_callback(f"  {line.split()[-1] if line.split() else line}")

            # 6. Create eula.txt
            if progress_callback:
                progress_callback("[6/11] Creating EULA (eula=true)...")
            eula_content = self.create_eula_txt()
            await self.execute_command(
                f"echo '{eula_content}' > /opt/minecraft/eula.txt", progress_callback
            )

            # 7. Create server.properties
            if progress_callback:
                progress_callback("[7/11] Writing server.properties...")
            props_content = self.escape_for_shell(self.create_server_properties())
            await self.execute_command(
                f"cat > /opt/minecraft/server.properties << 'EOF'\n{props_content}\nEOF",
                progress_callback,
            )

            # 8. Configure startup script
            if progress_callback:
                progress_callback("[8/11] Configuring startup script...")

            # Make run scripts executable
            await self.execute_command(
                "cd /opt/minecraft && chmod +x run.sh 2>/dev/null || true",
                progress_callback,
            )

            # Check if run.sh exists
            stdout, _ = await self.execute_command(
                "test -f /opt/minecraft/run.sh && echo 'exists' || echo 'missing'", None
            )
            if progress_callback:
                if "exists" in stdout:
                    progress_callback("Found run.sh script (will use for startup)")
                else:
                    progress_callback("No run.sh found (will use direct java command)")

            # 9. Set ownership
            if progress_callback:
                progress_callback("[9/11] Setting file ownership to minecraft:minecraft...")
            await self.execute_command(
                "chown -R minecraft:minecraft /opt/minecraft", progress_callback
            )

            # 10. Create systemd service
            if progress_callback:
                progress_callback("[10/11] Creating systemd service 'minecraft'...")
            service_content = self._create_systemd_service()
            await self.execute_command(
                f"cat > /etc/systemd/system/minecraft.service << 'EOF'\n{service_content}\nEOF",
                progress_callback,
            )
            if progress_callback:
                progress_callback("Service will use run.sh if available, otherwise direct java command")

            # 11. Start server
            if progress_callback:
                progress_callback("[11/11] Starting Forge Minecraft server...")
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
                progress_callback("NOTE: Forge is installed but no mods are included.")
                progress_callback("To add mods, upload .jar files to /opt/minecraft/mods/")
                progress_callback("Then restart: systemctl restart minecraft")
                progress_callback("")
                progress_callback("=" * 50)
                progress_callback("FORGE SERVER INSTALLATION COMPLETE")
                progress_callback("=" * 50)

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
