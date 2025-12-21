# Copyright (c) 2025 Mark Mercado <mamercad@gmail.com>
"""CurseForge API service for modpack downloads."""

import re
from dataclasses import dataclass

import aiohttp


class CurseForgeError(Exception):
    """CurseForge API error."""

    pass


@dataclass
class ModpackInfo:
    """Information about a CurseForge modpack."""

    project_id: int
    name: str
    slug: str
    summary: str
    modloader: str | None  # "forge", "fabric", or None
    minecraft_version: str | None
    server_pack_url: str | None
    server_pack_file_id: int | None
    latest_file_id: int | None


class CurseForgeService:
    """Service for interacting with the CurseForge API."""

    BASE_URL = "https://api.curseforge.com"
    MINECRAFT_GAME_ID = 432

    # Modloader type IDs from CurseForge API
    MODLOADER_TYPES = {
        1: "forge",
        4: "fabric",
        5: "quilt",
        6: "neoforge",
    }

    def __init__(self, api_key: str):
        """Initialize CurseForge service.

        Args:
            api_key: CurseForge API key from https://console.curseforge.com
        """
        self.api_key = api_key

    def _get_headers(self) -> dict:
        """Get API request headers."""
        return {
            "x-api-key": self.api_key,
            "Accept": "application/json",
        }

    @staticmethod
    def parse_url(url: str) -> str | None:
        """Extract modpack slug from a CurseForge URL.

        Args:
            url: CurseForge modpack URL

        Returns:
            Modpack slug or None if not a valid URL
        """
        # Match URLs like:
        # https://www.curseforge.com/minecraft/modpacks/jsmp-cobblemon
        # https://curseforge.com/minecraft/modpacks/all-the-mods-9
        pattern = r"(?:https?://)?(?:www\.)?curseforge\.com/minecraft/modpacks/([a-zA-Z0-9_-]+)"
        match = re.match(pattern, url)
        if match:
            return match.group(1)
        return None

    async def search_modpack(self, slug: str) -> tuple[int | None, str]:
        """Search for a modpack by slug to get its project ID.

        Args:
            slug: Modpack slug from URL

        Returns:
            Tuple of (Project ID or None, debug info string)
        """
        debug_info = []
        try:
            async with aiohttp.ClientSession() as session:
                # First, try direct slug search
                params = {
                    "gameId": self.MINECRAFT_GAME_ID,
                    "classId": 4471,  # Modpacks category
                    "slug": slug,
                }
                async with session.get(
                    f"{self.BASE_URL}/v1/mods/search",
                    headers=self._get_headers(),
                    params=params,
                ) as resp:
                    if resp.status == 403:
                        return None, (
                            "CurseForge API key is invalid or expired. "
                            "Get a new key from https://console.curseforge.com"
                        )
                    debug_info.append(f"Slug search: status={resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        mods = data.get("data", [])
                        debug_info.append(f"Slug search: {len(mods)} results")
                        # Find exact slug match (case-insensitive)
                        for mod in mods:
                            if mod.get("slug", "").lower() == slug.lower():
                                return mod.get("id"), "; ".join(debug_info)
                        # Show what slugs were returned
                        if mods:
                            found_slugs = [m.get("slug") for m in mods[:5]]
                            debug_info.append(f"Found slugs: {found_slugs}")

                # If slug search failed, try searchFilter with the slug as text
                # Convert slug to search terms (replace hyphens with spaces)
                search_terms = slug.replace("-", " ")
                params = {
                    "gameId": self.MINECRAFT_GAME_ID,
                    "classId": 4471,  # Modpacks category
                    "searchFilter": search_terms,
                }
                async with session.get(
                    f"{self.BASE_URL}/v1/mods/search",
                    headers=self._get_headers(),
                    params=params,
                ) as resp:
                    debug_info.append(f"Text search: status={resp.status}")
                    if resp.status == 200:
                        data = await resp.json()
                        mods = data.get("data", [])
                        debug_info.append(f"Text search: {len(mods)} results")
                        # Find exact slug match (case-insensitive)
                        for mod in mods:
                            if mod.get("slug", "").lower() == slug.lower():
                                return mod.get("id"), "; ".join(debug_info)
                        # Show what slugs were returned
                        if mods:
                            found_slugs = [m.get("slug") for m in mods[:5]]
                            debug_info.append(f"Found slugs: {found_slugs}")

                return None, "; ".join(debug_info)
        except Exception as e:
            debug_info.append(f"Exception: {e}")
            return None, "; ".join(debug_info)

    async def get_modpack_info(self, project_id: int) -> ModpackInfo | None:
        """Get detailed modpack information.

        Args:
            project_id: CurseForge project ID

        Returns:
            ModpackInfo or None if not found
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Get mod info
                async with session.get(
                    f"{self.BASE_URL}/v1/mods/{project_id}",
                    headers=self._get_headers(),
                ) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    mod = data.get("data", {})

                name = mod.get("name", "Unknown")
                slug = mod.get("slug", "")
                summary = mod.get("summary", "")

                # Get latest file info
                latest_files = mod.get("latestFiles", [])
                latest_file = None
                server_pack_url = None
                server_pack_file_id = None
                modloader = None
                minecraft_version = None

                # Find the latest server pack or main file
                for file in latest_files:
                    # Check for server pack in serverPackFileId
                    if file.get("serverPackFileId"):
                        server_pack_file_id = file.get("serverPackFileId")
                        latest_file = file
                        break
                    # Check if this file is a server pack
                    if file.get("isServerPack"):
                        server_pack_file_id = file.get("id")
                        latest_file = file
                        break

                # If no server pack found, use latest file
                if not latest_file and latest_files:
                    latest_file = latest_files[0]

                if latest_file:
                    # Extract modloader from file
                    game_versions = latest_file.get("gameVersions", [])
                    for gv in game_versions:
                        gv_lower = gv.lower()
                        if "forge" in gv_lower:
                            modloader = "forge"
                        elif "fabric" in gv_lower:
                            modloader = "fabric"
                        elif "neoforge" in gv_lower:
                            modloader = "neoforge"
                        elif "quilt" in gv_lower:
                            modloader = "quilt"
                        # Check for MC version (format like "1.20.1")
                        elif re.match(r"^\d+\.\d+(\.\d+)?$", gv):
                            minecraft_version = gv

                    # Try to get modloader from sortableGameVersions
                    for sgv in latest_file.get("sortableGameVersions", []):
                        type_id = sgv.get("gameVersionTypeId")
                        if type_id in self.MODLOADER_TYPES:
                            modloader = self.MODLOADER_TYPES[type_id]
                            break

                # Get server pack download URL if we have a server pack file ID
                if server_pack_file_id:
                    server_pack_url = await self._get_download_url(
                        session, project_id, server_pack_file_id
                    )

                return ModpackInfo(
                    project_id=project_id,
                    name=name,
                    slug=slug,
                    summary=summary,
                    modloader=modloader,
                    minecraft_version=minecraft_version,
                    server_pack_url=server_pack_url,
                    server_pack_file_id=server_pack_file_id,
                    latest_file_id=latest_file.get("id") if latest_file else None,
                )

        except Exception as e:
            raise CurseForgeError(f"Failed to get modpack info: {e}") from e

    async def _get_download_url(
        self, session: aiohttp.ClientSession, project_id: int, file_id: int
    ) -> str | None:
        """Get download URL for a file.

        Args:
            session: aiohttp session
            project_id: CurseForge project ID
            file_id: File ID to download

        Returns:
            Download URL or None
        """
        try:
            async with session.get(
                f"{self.BASE_URL}/v1/mods/{project_id}/files/{file_id}/download-url",
                headers=self._get_headers(),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("data")
        except Exception:
            return None

    async def get_modpack_files(self, project_id: int, limit: int = 10) -> list[dict]:
        """Get list of available files for a modpack.

        Args:
            project_id: CurseForge project ID
            limit: Maximum number of files to return

        Returns:
            List of file info dictionaries
        """
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(
                    f"{self.BASE_URL}/v1/mods/{project_id}/files",
                    headers=self._get_headers(),
                    params={"pageSize": limit},
                ) as resp,
            ):
                if resp.status != 200:
                    return []
                data = await resp.json()
                files = data.get("data", [])

                result = []
                for file in files:
                    file_info = {
                        "id": file.get("id"),
                        "name": file.get("displayName") or file.get("fileName"),
                        "date": file.get("fileDate"),
                        "is_server_pack": file.get("isServerPack", False),
                        "server_pack_file_id": file.get("serverPackFileId"),
                        "game_versions": file.get("gameVersions", []),
                    }
                    result.append(file_info)

                return result
        except Exception:
            return []

    async def fetch_from_url(self, url: str) -> ModpackInfo:
        """Fetch modpack info from a CurseForge URL.

        Args:
            url: CurseForge modpack URL

        Returns:
            ModpackInfo

        Raises:
            CurseForgeError: If URL is invalid or modpack not found
        """
        slug = self.parse_url(url)
        if not slug:
            raise CurseForgeError(
                "Invalid CurseForge URL. Expected format: "
                "https://www.curseforge.com/minecraft/modpacks/modpack-name"
            )

        project_id, debug_info = await self.search_modpack(slug)
        if not project_id:
            raise CurseForgeError(
                f"Modpack '{slug}' not found. Debug: {debug_info}"
            )

        info = await self.get_modpack_info(project_id)
        if not info:
            raise CurseForgeError(f"Failed to get info for modpack '{slug}'")

        return info
