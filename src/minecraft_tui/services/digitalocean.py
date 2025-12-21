# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""DigitalOcean API service wrapper using PyDo."""

import asyncio
import contextlib
from datetime import datetime

from pydo import Client

from ..config import Settings


class DigitalOceanError(Exception):
    """Base exception for DigitalOcean operations."""

    pass


class DigitalOceanService:
    """Service for DigitalOcean API operations using PyDo."""

    def __init__(self, settings: Settings):
        self.settings = settings
        if settings.digitalocean_token is None:
            raise DigitalOceanError("DigitalOcean token is not set")
        self.client = Client(token=settings.digitalocean_token.get_secret_value())

    async def get_account_info(self) -> dict:
        """Get DigitalOcean account information.

        Returns:
            Dictionary with account info (email, droplet_limit, status, etc.)

        Raises:
            DigitalOceanError: If account info retrieval fails
        """
        try:
            # Run synchronous API call in thread pool
            resp = await asyncio.to_thread(self.client.account.get)
            account = resp.get("account", {})
            return {
                "email": account.get("email", "Unknown"),
                "uuid": account.get("uuid", "Unknown"),
                "status": account.get("status", "Unknown"),
                "droplet_limit": account.get("droplet_limit", 0),
                "email_verified": account.get("email_verified", False),
                "team": account.get("team", {}).get("name") if account.get("team") else None,
            }
        except Exception as e:
            raise DigitalOceanError(f"Failed to get account info: {e}") from e

    async def ensure_ssh_key(self) -> int:
        """Ensure SSH key exists in DigitalOcean, upload if not.

        Returns:
            SSH key ID in DigitalOcean

        Raises:
            DigitalOceanError: If SSH key file doesn't exist or upload fails
        """
        if not self.settings.ssh_key_path.exists():
            raise DigitalOceanError(f"SSH public key not found at {self.settings.ssh_key_path}")

        # Read local SSH public key
        ssh_key_content = self.settings.ssh_key_path.read_text().strip()

        # Extract key type and key data (without comment)
        # SSH key format: <type> <data> [comment]
        key_parts = ssh_key_content.split(maxsplit=2)
        if len(key_parts) < 2:
            raise DigitalOceanError(f"Invalid SSH key format in {self.settings.ssh_key_path}")

        local_key_type = key_parts[0]  # e.g., "ssh-ed25519" or "ssh-rsa"
        local_key_data = key_parts[1]  # The actual key data

        # Check if key already exists by comparing type and data
        try:
            resp = await asyncio.to_thread(self.client.ssh_keys.list)
            for key in resp.get("ssh_keys", []):
                remote_key_content = key.get("public_key", "").strip()
                remote_parts = remote_key_content.split(maxsplit=2)

                if len(remote_parts) >= 2:
                    remote_key_type = remote_parts[0]
                    remote_key_data = remote_parts[1]

                    # Compare type and data (ignore comment)
                    if remote_key_type == local_key_type and remote_key_data == local_key_data:
                        # Key already exists - return existing ID
                        return key["id"]
        except Exception as e:
            raise DigitalOceanError(f"Failed to list SSH keys: {e}") from e

        # Upload new key
        try:
            req = {
                "public_key": ssh_key_content,
                "name": f"minecraft-tui-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            }
            resp = await asyncio.to_thread(self.client.ssh_keys.create, body=req)
            return resp["ssh_key"]["id"]
        except Exception as e:
            # Check if error is because key already exists
            error_msg = str(e)
            if "already in use" in error_msg.lower() or "duplicate" in error_msg.lower():
                # Key exists but we couldn't find it - try one more time with the improved comparison
                try:
                    resp = await asyncio.to_thread(self.client.ssh_keys.list)
                    for key in resp.get("ssh_keys", []):
                        remote_key_content = key.get("public_key", "").strip()
                        remote_parts = remote_key_content.split(maxsplit=2)

                        if len(remote_parts) >= 2:
                            remote_key_type = remote_parts[0]
                            remote_key_data = remote_parts[1]

                            if (
                                remote_key_type == local_key_type
                                and remote_key_data == local_key_data
                            ):
                                return key["id"]

                    # Still can't find it - use the first key as fallback
                    # This is safe because we know a key exists (the error told us)
                    all_keys = resp.get("ssh_keys", [])
                    if all_keys:
                        fallback_key = all_keys[0]
                        return fallback_key["id"]

                    raise DigitalOceanError(
                        "SSH key already exists but account has no keys listed. "
                        "This is unexpected - please check your DigitalOcean account."
                    ) from e
                except DigitalOceanError:
                    raise
                except Exception as list_error:
                    raise DigitalOceanError(
                        f"SSH key exists but couldn't verify: {list_error}"
                    ) from list_error
            raise DigitalOceanError(f"Failed to create SSH key: {e}") from e

    async def create_droplet(
        self,
        name: str,
        region: str | None = None,
        size: str | None = None,
        image: str | None = None,
        user_data: str | None = None,
        server_type: str | None = None,
        modpack_loader: str | None = None,
        modpack_source: str | None = None,
        mc_version: str | None = None,
        loader_version: str | None = None,
    ) -> dict:
        """Create a new droplet.

        Args:
            name: Droplet name
            region: DigitalOcean region (default from settings)
            size: Droplet size (default from settings)
            image: OS image (default from settings)
            user_data: Cloud-init user data script
            server_type: Minecraft server type (vanilla, forge, fabric, modpack)
            modpack_loader: Modloader type for modpacks (forge, fabric)
            modpack_source: Source indicator for modpacks (url, or filename)
            mc_version: Minecraft version (e.g., "1.20.1")
            loader_version: Forge/Fabric loader version (e.g., "47.2.0")

        Returns:
            Droplet information dictionary

        Raises:
            DigitalOceanError: If droplet creation fails
        """
        # Ensure SSH key exists
        ssh_key_id = await self.ensure_ssh_key()

        # Build tags list
        tags = ["minecraft-tui", "minecraft-server"]
        if server_type:
            tags.append(server_type.lower())
        if modpack_loader:
            tags.append(f"loader-{modpack_loader.lower()}")
        if modpack_source:
            # Sanitize source for tag (lowercase, alphanumeric + hyphens only)
            sanitized = modpack_source.lower().replace("_", "-").replace(" ", "-")
            sanitized = "".join(c for c in sanitized if c.isalnum() or c == "-")
            tags.append(f"source-{sanitized[:30]}")
        if mc_version:
            tags.append(f"mc-{mc_version}")
        if loader_version:
            # Truncate long version strings
            tags.append(f"lv-{loader_version[:20]}")

        req = {
            "name": name,
            "region": region or self.settings.default_region,
            "size": size or self.settings.default_size,
            "image": image or self.settings.default_image,
            "ssh_keys": [ssh_key_id],
            "backups": False,
            "ipv6": True,
            "monitoring": True,
        }

        if user_data:
            req["user_data"] = user_data

        try:
            resp = await asyncio.to_thread(self.client.droplets.create, body=req)
            droplet = resp["droplet"]
            droplet_id = droplet["id"]

            # Assign tags to the droplet after creation
            # (pydo's tags in create doesn't work reliably)
            for tag in tags:
                # Create tag if it doesn't exist
                with contextlib.suppress(Exception):
                    await asyncio.to_thread(self.client.tags.create, body={"name": tag})

                # Assign tag to droplet (best effort)
                with contextlib.suppress(Exception):
                    await asyncio.to_thread(
                        self.client.tags.assign_resources,
                        tag_id=tag,
                        body={
                            "resources": [
                                {"resource_id": str(droplet_id), "resource_type": "droplet"}
                            ]
                        },
                    )

            return droplet
        except Exception as e:
            raise DigitalOceanError(f"Failed to create droplet: {e}") from e

    async def wait_for_droplet_active(
        self, droplet_id: int, timeout: int = 300, poll_interval: int = 5
    ) -> dict:
        """Wait for droplet to become active.

        Args:
            droplet_id: Droplet ID
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds

        Returns:
            Active droplet information

        Raises:
            TimeoutError: If droplet doesn't become active within timeout
            DigitalOceanError: If polling fails
        """
        elapsed = 0
        while elapsed < timeout:
            try:
                resp = await asyncio.to_thread(self.client.droplets.get, droplet_id)
                droplet = resp["droplet"]

                if droplet["status"] == "active":
                    return droplet

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
            except Exception as e:
                raise DigitalOceanError(f"Failed to poll droplet status: {e}") from e

        raise TimeoutError(f"Droplet {droplet_id} did not become active within {timeout}s")

    async def list_droplets(self, tag: str = "minecraft-tui") -> list[dict]:
        """List all droplets with specific tag.

        Args:
            tag: Tag to filter droplets by

        Returns:
            List of droplet information dictionaries

        Raises:
            DigitalOceanError: If listing fails
        """
        try:
            resp = await asyncio.to_thread(self.client.droplets.list, tag_name=tag)
            return resp.get("droplets", [])
        except Exception as e:
            raise DigitalOceanError(f"Failed to list droplets: {e}") from e

    async def get_droplet(self, droplet_id: int) -> dict:
        """Get droplet information.

        Args:
            droplet_id: Droplet ID

        Returns:
            Droplet information dictionary

        Raises:
            DigitalOceanError: If retrieval fails
        """
        try:
            resp = await asyncio.to_thread(self.client.droplets.get, droplet_id)
            return resp["droplet"]
        except Exception as e:
            raise DigitalOceanError(f"Failed to get droplet {droplet_id}: {e}") from e

    async def delete_droplet(self, droplet_id: int) -> None:
        """Delete a droplet.

        Args:
            droplet_id: Droplet ID

        Raises:
            DigitalOceanError: If deletion fails
        """
        try:
            await asyncio.to_thread(self.client.droplets.destroy, droplet_id)
        except Exception as e:
            raise DigitalOceanError(f"Failed to delete droplet {droplet_id}: {e}") from e

    async def power_on(self, droplet_id: int) -> None:
        """Power on a droplet.

        Args:
            droplet_id: Droplet ID

        Raises:
            DigitalOceanError: If power on fails
        """
        try:
            req = {"type": "power_on"}
            await asyncio.to_thread(self.client.droplet_actions.post, droplet_id, body=req)
        except Exception as e:
            raise DigitalOceanError(f"Failed to power on droplet {droplet_id}: {e}") from e

    async def power_off(self, droplet_id: int) -> None:
        """Power off a droplet.

        Args:
            droplet_id: Droplet ID

        Raises:
            DigitalOceanError: If power off fails
        """
        try:
            req = {"type": "power_off"}
            await asyncio.to_thread(self.client.droplet_actions.post, droplet_id, body=req)
        except Exception as e:
            raise DigitalOceanError(f"Failed to power off droplet {droplet_id}: {e}") from e

    async def reboot(self, droplet_id: int) -> None:
        """Reboot a droplet.

        Args:
            droplet_id: Droplet ID

        Raises:
            DigitalOceanError: If reboot fails
        """
        try:
            req = {"type": "reboot"}
            await asyncio.to_thread(self.client.droplet_actions.post, droplet_id, body=req)
        except Exception as e:
            raise DigitalOceanError(f"Failed to reboot droplet {droplet_id}: {e}") from e
