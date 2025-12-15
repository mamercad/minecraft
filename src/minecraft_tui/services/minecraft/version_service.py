"""Minecraft version service for fetching available versions."""

import time

import aiohttp

from ...models.server import MinecraftVersion


class MinecraftVersionService:
    """Service for fetching and managing Minecraft versions."""

    MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
    CACHE_TTL = 300  # 5 minutes

    def __init__(self):
        self._cache: dict | None = None
        self._cache_time: float | None = None

    def _is_cache_valid(self) -> bool:
        """Check if cached data is still valid."""
        if self._cache is None or self._cache_time is None:
            return False
        return (time.time() - self._cache_time) < self.CACHE_TTL

    async def _get_manifest(self) -> dict:
        """Fetch version manifest from Mojang API.

        Returns:
            Version manifest dictionary

        Raises:
            Exception: If fetch fails
        """
        # Return cached data if valid
        if self._is_cache_valid():
            return self._cache

        # Fetch from API
        async with (
            aiohttp.ClientSession() as session,
            session.get(self.MANIFEST_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp,
        ):
            manifest = await resp.json()

        # Update cache
        self._cache = manifest
        self._cache_time = time.time()

        return manifest

    async def fetch_versions(
        self,
        limit: int = 20,
        include_snapshots: bool = False,
    ) -> list[MinecraftVersion]:
        """Fetch available Minecraft versions.

        Args:
            limit: Maximum number of versions to return
            include_snapshots: Whether to include snapshot versions

        Returns:
            List of MinecraftVersion objects

        Raises:
            Exception: If fetch fails
        """
        try:
            manifest = await self._get_manifest()
            versions = manifest.get("versions", [])

            # Filter by type
            if not include_snapshots:
                versions = [v for v in versions if v.get("type") == "release"]

            # Limit count
            versions = versions[:limit]

            # Convert to MinecraftVersion models
            return [MinecraftVersion(version=v["id"], release_type=v["type"]) for v in versions]
        except Exception:
            # Return fallback versions on error
            return self._get_fallback_versions()

    async def get_latest_release(self) -> str:
        """Get the latest release version.

        Returns:
            Latest release version ID

        Raises:
            Exception: If fetch fails
        """
        try:
            manifest = await self._get_manifest()
            return manifest.get("latest", {}).get("release", "1.21.11")
        except Exception:
            # Return fallback on error
            return "1.21.11"

    def format_for_select(self, versions: list[MinecraftVersion]) -> list[tuple[str, str]]:
        """Convert versions to Select widget format.

        Args:
            versions: List of MinecraftVersion objects

        Returns:
            List of (display_text, value) tuples for Select widget
        """
        return [(v.version, v.version) for v in versions]

    def _get_fallback_versions(self) -> list[MinecraftVersion]:
        """Get hardcoded fallback versions when API is unavailable.

        Returns:
            List of common Minecraft versions
        """
        fallback_version_ids = [
            "1.21.11",
            "1.21.1",
            "1.21",
            "1.20.6",
            "1.20.5",
            "1.20.4",
            "1.20.3",
            "1.20.2",
            "1.20.1",
            "1.20",
            "1.19.4",
            "1.19.3",
            "1.19.2",
            "1.19.1",
            "1.19",
            "1.18.2",
            "1.18.1",
            "1.18",
            "1.17.1",
            "1.17",
        ]
        return [MinecraftVersion(version=v, release_type="release") for v in fallback_version_ids]
