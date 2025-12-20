"""Modloader version fetching service."""

import aiohttp


class LoaderVersionService:
    """Service for fetching Forge and Fabric loader versions."""

    async def fetch_fabric_versions(self, limit: int = 20) -> list[str]:
        """Fetch available Fabric loader versions.

        Args:
            limit: Maximum number of versions to return

        Returns:
            List of version strings (newest first)
        """
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get("https://meta.fabricmc.net/v2/versions/loader") as resp,
            ):
                if resp.status != 200:
                    return []
                versions = await resp.json()
                # Return stable versions first
                return [v["version"] for v in versions[:limit]]
        except Exception:
            return []

    async def fetch_forge_versions(self, mc_version: str = "1.20.1", limit: int = 20) -> list[str]:
        """Fetch available Forge versions for a Minecraft version.

        Args:
            mc_version: Minecraft version to get Forge versions for
            limit: Maximum number of versions to return

        Returns:
            List of version strings (newest first)
        """
        try:
            # Forge promotions API
            async with (
                aiohttp.ClientSession() as session,
                session.get("https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json") as resp,
            ):
                if resp.status != 200:
                    return []
                data = await resp.json()
                promos = data.get("promos", {})

                # Get versions for the specified MC version
                versions = []

                # Add recommended version if available
                recommended_key = f"{mc_version}-recommended"
                if recommended_key in promos:
                    versions.append(f"{promos[recommended_key]} (recommended)")

                # Add latest version if available
                latest_key = f"{mc_version}-latest"
                if latest_key in promos:
                    versions.append(f"{promos[latest_key]} (latest)")

                # If no versions found for this MC version, return empty list
                if not versions:
                    return []

                return versions[:limit]
        except Exception:
            return []

    async def fetch_forge_versions_detailed(self, mc_version: str = "1.20.1", limit: int = 20) -> list[str]:
        """Fetch all Forge versions for a Minecraft version from Maven.

        Args:
            mc_version: Minecraft version to get Forge versions for
            limit: Maximum number of versions to return

        Returns:
            List of version strings (newest first)
        """
        try:
            # Use the Forge maven metadata API to get all versions
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    "https://files.minecraftforge.net/maven/net/minecraftforge/forge/maven-metadata.json"
                ) as resp,
            ):
                if resp.status != 200:
                    # Fall back to promotions API
                    return await self.fetch_forge_versions(mc_version, limit)

                data = await resp.json()
                # Data is a dict with MC versions as keys
                if mc_version in data:
                    versions = data[mc_version]
                    # Return newest versions first
                    return versions[-limit:][::-1]
                return []
        except Exception:
            # Fall back to promotions API
            return await self.fetch_forge_versions(mc_version, limit)
