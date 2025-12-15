"""Custom modpack Minecraft server installer."""

from collections.abc import Callable

from .base import BaseMinecraftInstaller, InstallationError


class ModpackInstaller(BaseMinecraftInstaller):
    """Installer for custom Minecraft modpacks."""

    async def install(self, progress_callback: Callable[[str], None] | None = None):
        """Install custom modpack.

        Args:
            progress_callback: Optional callback for installation progress

        Raises:
            InstallationError: If installation fails or modpack_url is not set
        """
        if not self.config.modpack_url:
            raise InstallationError("Modpack URL is required for modpack installations")

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

            # 4. Download modpack
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
            service_content = self._create_systemd_service()
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

    def _create_systemd_service(self) -> str:
        """Generate systemd service file for modpack.

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
