# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **SSH Shell**: Interactive terminal access to servers - suspends TUI and opens full SSH session as root
- **Start/Stop Game Buttons**: Control Minecraft service directly from TUI (systemctl start/stop minecraft)
- **Installation Log Viewing**: View server installation logs via "Install Log" button in server console
- **Installation Log Capture**: All installation steps are saved to `/opt/minecraft/install.log` on the server
- **Droplet ID in Delete Dialog**: Delete confirmation now shows droplet ID for verification
- **Minecraft Version Selection for Modpacks**: Choose MC version in addition to loader version for modded servers
- **CurseForge Integration**: Paste CurseForge modpack URLs to auto-detect modloader and download server packs
- **Fabric Server Support**: Full support for Fabric modloader installations
- **Modloader Version Dropdowns**: Select Forge/Fabric versions from live API data instead of manual input
- **Local Modpack Upload**: Upload modpack ZIPs directly via SFTP instead of requiring a URL
- **Game Status Column**: Server list shows live Minecraft service status via SSH checks (✓ running, stopped, ✗ failed)
- **Enhanced Server Tagging**: Droplets tagged with modloader type (forge/fabric) and source filename
- **Droplet ID Column**: Server list now shows DigitalOcean droplet IDs
- **Pricing Column**: Server list shows monthly cost ($/mo) for each droplet
- **In-App Documentation**: Press `?` for README, `c` for Changelog popup windows
- RCON service for remote console access to Minecraft servers with full protocol support
- Server console screen with live command execution and log viewing
- Comprehensive RCON error diagnostics with context-specific troubleshooting steps
- Automatic RCON password generation and secure storage in server.properties
- Debug logging to `/tmp/minecraft_tui_rcon_debug.log` for RCON troubleshooting
- Detailed SSH diagnostic commands in error messages for common RCON issues
- pytest-textual-snapshot for visual regression testing of TUI screens
- Snapshot tests for splash screen, welcome screen, and main menu
- Mock fixtures for DigitalOcean, SSH, and RCON services to support comprehensive testing
- SCREENSHOTS.md with text-based mockups and documentation for all TUI screens
- Pytest configuration with shared fixtures and animation disabling for consistent tests

### Fixed
- Thread-safe progress updates using `call_from_thread` for SSH operations
- Duplicate "No servers found" rows prevented with fetch flag
- RCON now binds to 0.0.0.0 (all interfaces) instead of localhost for external access
- Server control buttons now appear on a single row instead of split across two rows
- RCON authentication properly handles servers that send only one response packet
- Connection timeout errors provide specific troubleshooting based on error type (connection refused vs timeout vs auth failure)
- Select widget options now use correct (label, value) format

### Security
- Removed plain-text RCON password exposure in debug logs
- RCON password now only logs length instead of actual password value

### Changed
- Modpack type display now shows "modpack (fabric) - filename.zip" format
- Server list columns expanded: ID, Name, Type, IP, Size, $/mo, Region, Status, Game

## [0.1.0] - 2024-12-15

### Added
- Initial release of Minecraft TUI for DigitalOcean
- Textual-based terminal user interface for managing Minecraft servers
- Splash screen with ASCII art and randomized Minecraft creepers
- Welcome screen with DigitalOcean token configuration
- Main menu with account information display
- Server creation wizard with 5-step process:
  - Server type selection (Vanilla, Forge, Modpack)
  - Version configuration
  - Server settings (name, players, region, droplet size, SSH key, EULA)
  - server.properties editor with editable TextArea
  - Review screen with complete configuration preview
- Server list screen with live DigitalOcean data and auto-refresh (30-second intervals)
- Server detail screen with:
  - Real-time server status display
  - Connection information with highlighted IP address
  - Droplet specifications (size, region, vCPUs, memory, disk)
  - Power controls (Power On/Off, Reboot)
  - Server deletion with confirmation dialog
- Progress screen with real-time installation streaming
- Automatic droplet provisioning on DigitalOcean
- Cloud-init integration for automatic security hardening:
  - fail2ban configuration for SSH brute-force protection (3 max retries, 30-minute ban)
  - UFW firewall with default deny incoming policy
  - Automatic firewall rules for SSH (22), Minecraft (25565), and RCON (25575)
  - Disabled root password login (SSH key authentication only)
  - UTC timezone configuration
  - Optional Minecraft DDoS filter for fail2ban
- Automated Minecraft server installation via SSH:
  - Java 21 installation (OpenJDK)
  - Automatic server JAR download from Mojang API
  - systemd service creation for automatic server management
  - EULA acceptance handling
  - Configurable server.properties with parser
- Vi-style key bindings for navigation (j/k, g/G)
- SSH key management with automatic discovery and validation
- Auto-generated server names with timestamp
- Support for multiple Minecraft server types:
  - Vanilla servers with version manifest API integration
  - Forge servers (modded)
  - Modpack servers
- Idempotent SSH key operations to avoid duplicates in DigitalOcean

### Fixed
- Wrapped synchronous PyDo API calls with asyncio.to_thread for proper async handling
- Proper screen refresh method usage in Textual
- SSH key comparison now parses key components (type and data) correctly, ignoring comments
- Dark mode attribute initialization in app
- APT lock handling with exponential backoff retry logic (10 retries max)

### Security
- Cloud-init automatically configures fail2ban for SSH protection
- UFW firewall with restrictive default deny incoming policy
- Root password login disabled, SSH key authentication enforced
- RCON password generated using secrets.token_urlsafe(16) for cryptographic security

### Changed
- Default server type changed to Vanilla
- Server list refresh interval set to 30 seconds (toggleable)
- Droplet tags now include 'minecraft-tui' and 'minecraft-server' for filtering

## [0.0.0] - 2024-12-14

### Added
- Project initialization
- Basic project structure with pyproject.toml
- Development dependencies (pytest, ruff, textual-dev)
- Test suite configuration with pytest-asyncio
- Pydantic models for server configuration
- DigitalOcean service wrapper for PyDo client

---

[unreleased]: https://github.com/mamercad/minecraft/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mamercad/minecraft/compare/v0.0.0...v0.1.0
[0.0.0]: https://github.com/mamercad/minecraft/releases/tag/v0.0.0
