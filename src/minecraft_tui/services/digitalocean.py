"""DigitalOcean API service wrapper using PyDo."""

import asyncio
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

        # Normalize key content for comparison (remove extra whitespace)
        normalized_local_key = " ".join(ssh_key_content.split())

        # Check if key already exists by comparing normalized content
        try:
            resp = self.client.ssh_keys.list()
            for key in resp.get("ssh_keys", []):
                # Normalize the remote key for comparison
                remote_key = " ".join(key.get("public_key", "").split())
                if remote_key == normalized_local_key:
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
            resp = self.client.ssh_keys.create(body=req)
            return resp["ssh_key"]["id"]
        except Exception as e:
            # Check if error is because key already exists
            error_msg = str(e)
            if "already in use" in error_msg.lower() or "duplicate" in error_msg.lower():
                # Key exists but we couldn't find it in the list - try again
                try:
                    resp = self.client.ssh_keys.list()
                    for key in resp.get("ssh_keys", []):
                        remote_key = " ".join(key.get("public_key", "").split())
                        if remote_key == normalized_local_key:
                            return key["id"]
                    # If we still can't find it, raise a more helpful error
                    raise DigitalOceanError(
                        "SSH key already exists in DigitalOcean but couldn't be found. "
                        "Try removing duplicate keys from your DigitalOcean account."
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
    ) -> dict:
        """Create a new droplet.

        Args:
            name: Droplet name
            region: DigitalOcean region (default from settings)
            size: Droplet size (default from settings)
            image: OS image (default from settings)
            user_data: Cloud-init user data script

        Returns:
            Droplet information dictionary

        Raises:
            DigitalOceanError: If droplet creation fails
        """
        # Ensure SSH key exists
        ssh_key_id = await self.ensure_ssh_key()

        req = {
            "name": name,
            "region": region or self.settings.default_region,
            "size": size or self.settings.default_size,
            "image": image or self.settings.default_image,
            "ssh_keys": [ssh_key_id],
            "backups": False,
            "ipv6": True,
            "monitoring": True,
            "tags": ["minecraft-tui", "minecraft-server"],
        }

        if user_data:
            req["user_data"] = user_data

        try:
            resp = self.client.droplets.create(body=req)
            return resp["droplet"]
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
                resp = self.client.droplets.get(droplet_id)
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
            resp = self.client.droplets.list(tag_name=tag)
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
            resp = self.client.droplets.get(droplet_id)
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
            self.client.droplets.destroy(droplet_id)
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
            self.client.droplet_actions.post(droplet_id, body=req)
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
            self.client.droplet_actions.post(droplet_id, body=req)
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
            self.client.droplet_actions.post(droplet_id, body=req)
        except Exception as e:
            raise DigitalOceanError(f"Failed to reboot droplet {droplet_id}: {e}") from e
