"""Custom modpack Minecraft server installer."""

from collections.abc import Callable

import aiohttp

from .base import BaseMinecraftInstaller, InstallationError
from .loader_versions import LoaderVersionService


class ModpackInstaller(BaseMinecraftInstaller):
    """Installer for custom Minecraft modpacks."""

    async def get_latest_fabric_loader_version(self) -> str:
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
                    return versions[0]["version"]
                raise InstallationError("No Fabric loader versions found")
        except Exception as e:
            raise InstallationError(f"Failed to fetch Fabric loader version: {e}") from e

    async def get_forge_version(self) -> str:
        """Get the actual Forge version to install.

        Returns:
            Actual Forge version number (e.g., "47.2.0")
        """
        forge_version = self.config.modpack_loader_version

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

    async def install_forge(self, progress_callback: Callable[[str], None] | None = None):
        """Install Forge modloader.

        Args:
            progress_callback: Optional callback for installation progress
        """
        mc_version = self.config.minecraft_version

        # Resolve "latest" to actual version
        forge_version = await self.get_forge_version()

        if progress_callback:
            progress_callback(f"Installing Forge {forge_version} for Minecraft {mc_version}...")

        # Download Forge installer
        full_version = f"{mc_version}-{forge_version}"
        installer_url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{full_version}/forge-{full_version}-installer.jar"

        if progress_callback:
            progress_callback(f"Downloading Forge installer from: {installer_url}")
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

        # Run Forge installer
        if progress_callback:
            progress_callback("Running Forge installer (this may take a while)...")
        await self.execute_command(
            "cd /opt/minecraft && java -jar forge-installer.jar --installServer",
            progress_callback,
        )

        # Make run scripts executable
        await self.execute_command(
            "cd /opt/minecraft && chmod +x run.sh 2>/dev/null || true",
            progress_callback,
        )

    async def install_fabric(self, progress_callback: Callable[[str], None] | None = None):
        """Install Fabric modloader.

        Args:
            progress_callback: Optional callback for installation progress
        """
        mc_version = self.config.minecraft_version
        fabric_version = self.config.modpack_loader_version

        # Get latest version if not specified
        if not fabric_version or fabric_version == "latest":
            if progress_callback:
                progress_callback("Fetching latest Fabric loader version...")
            fabric_version = await self.get_latest_fabric_loader_version()

        if progress_callback:
            progress_callback(f"Installing Fabric {fabric_version} for Minecraft {mc_version}...")

        # Download Fabric server JAR
        server_url = f"https://meta.fabricmc.net/v2/versions/loader/{mc_version}/{fabric_version}/1.0.1/server/jar"
        await self.execute_command(
            f"wget -q -O /opt/minecraft/server.jar '{server_url}'",
            progress_callback,
        )

    async def extract_modpack(self, progress_callback: Callable[[str], None] | None = None):
        """Download or upload and extract modpack, copying contents to server.

        Args:
            progress_callback: Optional callback for installation progress
        """
        # Check if we're uploading a local file or downloading from URL
        if self.config.modpack_file_path:
            # Upload local file via SFTP
            if progress_callback:
                progress_callback("Uploading modpack from local file...")
            await self.upload_file(
                self.config.modpack_file_path,
                "/tmp/modpack.zip",
                progress_callback,
            )
        else:
            # Download from URL
            if progress_callback:
                progress_callback("Downloading modpack...")
            await self.execute_command(
                f"wget -q -O /tmp/modpack.zip '{self.config.modpack_url}'",
                progress_callback,
            )

        if progress_callback:
            progress_callback("Extracting modpack...")
        await self.execute_command(
            "mkdir -p /tmp/modpack && cd /tmp/modpack && unzip -o /tmp/modpack.zip",
            progress_callback,
        )

        # Detect modpack structure and copy appropriate files
        if progress_callback:
            progress_callback("Detecting modpack structure...")

        # Check for CurseForge-style overrides folder
        stdout, _ = await self.execute_command(
            "test -d /tmp/modpack/overrides && echo 'yes' || echo 'no'",
            progress_callback,
        )
        if stdout.strip() == "yes":
            if progress_callback:
                progress_callback("Found CurseForge-style overrides folder, copying...")
            await self.execute_command(
                "cp -r /tmp/modpack/overrides/* /opt/minecraft/",
                progress_callback,
            )

        # Check for Modrinth-style server-overrides folder
        stdout, _ = await self.execute_command(
            "test -d /tmp/modpack/server-overrides && echo 'yes' || echo 'no'",
            progress_callback,
        )
        if stdout.strip() == "yes":
            if progress_callback:
                progress_callback("Found Modrinth-style server-overrides folder, copying...")
            await self.execute_command(
                "cp -r /tmp/modpack/server-overrides/* /opt/minecraft/",
                progress_callback,
            )

        # Check for mods folder at root level
        stdout, _ = await self.execute_command(
            "test -d /tmp/modpack/mods && echo 'yes' || echo 'no'",
            progress_callback,
        )
        if stdout.strip() == "yes":
            if progress_callback:
                progress_callback("Found mods folder, copying...")
            await self.execute_command(
                "mkdir -p /opt/minecraft/mods && cp -r /tmp/modpack/mods/* /opt/minecraft/mods/",
                progress_callback,
            )

        # Check for config folder at root level
        stdout, _ = await self.execute_command(
            "test -d /tmp/modpack/config && echo 'yes' || echo 'no'",
            progress_callback,
        )
        if stdout.strip() == "yes":
            if progress_callback:
                progress_callback("Found config folder, copying...")
            await self.execute_command(
                "mkdir -p /opt/minecraft/config && cp -r /tmp/modpack/config/* /opt/minecraft/config/",
                progress_callback,
            )

        # Cleanup temp files
        await self.execute_command("rm -rf /tmp/modpack /tmp/modpack.zip", progress_callback)

    async def install_with_modloader(self, progress_callback: Callable[[str], None] | None = None):
        """Install modpack with specified modloader.

        Args:
            progress_callback: Optional callback for installation progress

        Raises:
            InstallationError: If installation fails
        """
        try:
            # 0. Wait for cloud-init to complete
            await self.wait_for_cloud_init(progress_callback)

            # 1. Install Java (include JDK for Forge)
            if progress_callback:
                progress_callback("Installing Java 21...")
            await self.execute_apt_with_retry(
                "DEBIAN_FRONTEND=noninteractive apt-get update && "
                "DEBIAN_FRONTEND=noninteractive apt-get install -y openjdk-21-jre-headless openjdk-21-jdk-headless unzip wget",
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

            # 4. Install the modloader
            if self.config.modpack_loader == "forge":
                await self.install_forge(progress_callback)
            elif self.config.modpack_loader == "fabric":
                await self.install_fabric(progress_callback)

            # 5. Extract and copy modpack contents
            await self.extract_modpack(progress_callback)

            # 6. Create eula.txt
            if progress_callback:
                progress_callback("Creating EULA...")
            eula_content = self.create_eula_txt()
            await self.execute_command(
                f"echo '{eula_content}' > /opt/minecraft/eula.txt", progress_callback
            )

            # 7. Create/update server.properties
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
            service_content = self._create_modloader_systemd_service()
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
            raise InstallationError(f"Modpack installation failed: {e}") from e

    async def install_server_pack(self, progress_callback: Callable[[str], None] | None = None):
        """Install complete server pack (original behavior).

        Args:
            progress_callback: Optional callback for installation progress

        Raises:
            InstallationError: If installation fails
        """
        try:
            # 0. Wait for cloud-init to complete
            await self.wait_for_cloud_init(progress_callback)

            # 1. Install dependencies
            if progress_callback:
                progress_callback("Installing dependencies...")
            await self.execute_apt_with_retry(
                "DEBIAN_FRONTEND=noninteractive apt-get update && "
                "DEBIAN_FRONTEND=noninteractive apt-get install -y openjdk-21-jre-headless openjdk-21-jdk-headless unzip wget",
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

            # 4. Download or upload modpack
            if self.config.modpack_file_path:
                if progress_callback:
                    progress_callback("Uploading modpack from local file...")
                await self.upload_file(
                    self.config.modpack_file_path,
                    "/opt/minecraft/modpack.zip",
                    progress_callback,
                )
            else:
                if progress_callback:
                    progress_callback("Downloading modpack...")
                await self.execute_command(
                    f"wget -q -O /opt/minecraft/modpack.zip '{self.config.modpack_url}'",
                    progress_callback,
                )

            # 5. Extract modpack
            if progress_callback:
                progress_callback("Extracting modpack...")
            await self.execute_command(
                "cd /opt/minecraft && unzip -o modpack.zip", progress_callback
            )

            # 6. Detect modpack type (look for forge installer, fabric loader, etc.)
            if progress_callback:
                progress_callback("Detecting modpack configuration...")

            # 7. Run any setup scripts included in modpack
            # Many modpacks include install.sh or similar
            stdout, _ = await self.execute_command(
                "cd /opt/minecraft && ls *.sh 2>/dev/null | head -n 1 || echo 'none'",
                progress_callback,
            )

            install_script = stdout.strip()
            if install_script and install_script != "none":
                if progress_callback:
                    progress_callback(f"Running modpack installer: {install_script}...")
                await self.execute_command(
                    f"cd /opt/minecraft && chmod +x {install_script} && bash {install_script}",
                    progress_callback,
                )

            # 8. Create eula.txt
            if progress_callback:
                progress_callback("Creating EULA...")
            eula_content = self.create_eula_txt()
            await self.execute_command(
                f"echo '{eula_content}' > /opt/minecraft/eula.txt", progress_callback
            )

            # 8. Update server.properties if it exists, otherwise create it
            if progress_callback:
                progress_callback("Configuring server...")
            props_content = self.escape_for_shell(self.create_server_properties())
            await self.execute_command(
                f"cat > /opt/minecraft/server.properties << 'EOF'\n{props_content}\nEOF",
                progress_callback,
            )

            # 10. Make any scripts executable
            await self.execute_command(
                "cd /opt/minecraft && chmod +x *.sh 2>/dev/null || true",
                progress_callback,
            )

            # 11. Set ownership
            if progress_callback:
                progress_callback("Setting permissions...")
            await self.execute_command(
                "chown -R minecraft:minecraft /opt/minecraft", progress_callback
            )

            # 12. Create systemd service
            if progress_callback:
                progress_callback("Creating systemd service...")
            service_content = self._create_server_pack_systemd_service()
            await self.execute_command(
                f"cat > /etc/systemd/system/minecraft.service << 'EOF'\n{service_content}\nEOF",
                progress_callback,
            )

            # 13. Start server
            if progress_callback:
                progress_callback("Starting server...")
            await self.execute_command("systemctl daemon-reload", progress_callback)
            await self.execute_command("systemctl enable minecraft", progress_callback)
            await self.execute_command("systemctl start minecraft", progress_callback)

            if progress_callback:
                progress_callback("Installation complete!")

        except Exception as e:
            raise InstallationError(f"Modpack installation failed: {e}") from e

    async def install(self, progress_callback: Callable[[str], None] | None = None):
        """Install custom modpack.

        If modpack_loader is specified, installs the modloader first then extracts mods.
        Otherwise, treats the ZIP as a complete server pack.

        Args:
            progress_callback: Optional callback for installation progress

        Raises:
            InstallationError: If installation fails or modpack_url is not set
        """
        if not self.config.modpack_url and not self.config.modpack_file_path:
            raise InstallationError("Modpack URL or file path is required for modpack installations")

        # Check if a modloader is specified
        if self.config.modpack_loader in ("forge", "fabric"):
            await self.install_with_modloader(progress_callback)
        else:
            await self.install_server_pack(progress_callback)

    def _create_modloader_systemd_service(self) -> str:
        """Generate systemd service file for modloader-based installation.

        Returns:
            Systemd service file content
        """
        if self.config.modpack_loader == "forge":
            # Forge uses run.sh if available
            exec_start = f"/bin/bash -c 'if [ -f run.sh ]; then ./run.sh; else java -Xmx{self.config.memory_mb}M -Xms{self.config.memory_mb}M -jar forge*.jar nogui; fi'"
        else:
            # Fabric uses server.jar directly
            exec_start = f"/usr/bin/java -Xmx{self.config.memory_mb}M -Xms{self.config.memory_mb}M -jar server.jar nogui"

        return f"""[Unit]
Description=Minecraft Modpack Server ({self.config.modpack_loader.capitalize()})
After=network.target

[Service]
Type=simple
User=minecraft
Group=minecraft
WorkingDirectory=/opt/minecraft
ExecStart={exec_start}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

    def _create_server_pack_systemd_service(self) -> str:
        """Generate systemd service file for complete server pack.

        Returns:
            Systemd service file content
        """
        # Try various common startup methods
        return f"""[Unit]
Description=Minecraft Modpack Server
After=network.target

[Service]
Type=simple
User=minecraft
Group=minecraft
WorkingDirectory=/opt/minecraft
ExecStart=/bin/bash -c 'if [ -f start.sh ]; then ./start.sh; elif [ -f run.sh ]; then ./run.sh; elif [ -f ServerStart.sh ]; then ./ServerStart.sh; else java -Xmx{self.config.memory_mb}M -Xms{self.config.memory_mb}M -jar $(ls -1 forge*.jar minecraft_server*.jar server.jar 2>/dev/null | head -n1) nogui; fi'
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
