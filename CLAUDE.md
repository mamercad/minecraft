# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Textual-based TUI application for managing Minecraft servers on DigitalOcean droplets. The app automates server provisioning, installation, and lifecycle management through an interactive terminal interface.

## Development Commands

### Running the Application
```bash
# Using uv (recommended)
uv run minecraft-tui

# With development console for debugging
textual console  # In one terminal
uv run minecraft-tui  # In another terminal
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/minecraft_tui --cov-report=html

# Run specific test file
uv run pytest tests/test_config.py
```

### Code Quality
```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Fix linting issues automatically
uv run ruff check --fix .
```

### Package Management
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package-name>

# Add dev dependency
uv add --dev <package-name>
```

## Architecture

### Application Flow
1. **App Initialization** (`app.py`): Shows splash screen, then checks for `DIGITALOCEAN_TOKEN`, routes to Welcome or MainMenu screen
2. **Splash Screen**: ASCII art splash using figlet with randomized Minecraft creepers in the background (3-7 creepers of varying sizes at random positions), auto-dismisses after 3 seconds or on any keystroke
3. **Screen Navigation**: Uses Textual's screen stack for navigation between Splash → Welcome/MainMenu → CreateServer/ServerList → ServerDetail/Console → Progress
3. **Server Creation Wizard**: 5-step wizard
   - Step 1: Server type selection
   - Step 2: Version configuration
   - Step 3: Server settings (name, players, region, droplet size, SSH key, EULA)
   - Step 4: server.properties editor (editable TextArea)
   - Step 5: Review (shows all settings + read-only server.properties preview)
4. **Droplet Provisioning**: Creates DigitalOcean droplet with cloud-init for automatic security hardening
5. **Async Operations**: All DigitalOcean API calls wrapped with `asyncio.to_thread()` because PyDo client is synchronous
6. **SSH Installation**: Uses paramiko for SSH connections to install Minecraft via shell commands

### Key Components

**Configuration (`config.py`)**
- Uses Pydantic Settings for environment variables and `.env` file
- Loads from `.env` or environment with case-insensitive matching
- All sensitive values use `SecretStr` (especially `digitalocean_token`)

**DigitalOcean Service (`services/digitalocean.py`)**
- Wraps PyDo client (synchronous) with `asyncio.to_thread()` for all API calls
- Handles SSH key management: compares key type and data (ignoring comments) to avoid duplicates
- Tags all droplets with `minecraft-tui` and `minecraft-server` for filtering
- Implements polling for droplet status (wait_for_droplet_active)
- Accepts cloud-init user data for automatic server configuration

**Cloud-Init Configuration (`utils/cloud_init.py`)**
- Generates cloud-init YAML for automatic security hardening
- Installs and configures fail2ban for SSH protection (3 retries, 30-minute ban)
- Configures UFW firewall (SSH port 22, Minecraft port 25565, RCON port 25575)
- Disables root password login (SSH key authentication only)
- Sets timezone to UTC
- Includes optional Minecraft DDoS filter for fail2ban

**RCON Service (`services/rcon_service.py`)**
- Wraps mcrcon library with async support using `asyncio.to_thread()`
- Retrieves RCON password from server.properties via SSH
- Connects to Minecraft RCON (port 25575) for remote console access
- Sends commands and retrieves responses
- Fetches server logs from systemd journal via SSH

**Minecraft Installers (`services/minecraft/`)**
- `base.py`: Abstract base class with SSH connection, command execution, and streaming progress
- `vanilla.py`, `forge.py`, `modpack.py`: Concrete installers for different server types
- All installers create systemd services for server management
- Installation runs via SSH commands with real-time progress streaming

**Screens (`screens/`)**
- Textual screens handle UI navigation and user interaction
- Each screen is self-contained with its own bindings and compose method
- Screens communicate via Textual's message system and screen stack
- `splash.py`: ASCII art splash screen using pyfiglet with randomized Minecraft creepers (3-7 creepers, 3 sizes: small/medium/large, random positions), auto-dismisses after 3s or on keystroke
- `main_menu.py`: Main menu with large Minecraft creeper ASCII art on the left side
- `create_server.py`: 5-step wizard including TextArea for editing server.properties
- `server_list.py`: Server list with auto-refresh every 30 seconds (toggleable), refreshes on resume from detail view
- `server_console.py`: Live server console with RCON command support and log viewing

**Widgets (`widgets/`)**
- `progress_log.py`: ProgressLog widget for streaming installation progress
- `server_card.py`: ServerCard widget for displaying server information
- `vi_radio_set.py`: ViRadioSet extends RadioSet with vi key bindings (j/k for navigation)

**Models (`models/`)**
- `server.py`: Pydantic models for ServerConfig (user's server settings)
- `droplet.py`: Models for DigitalOcean droplet data

### Important Patterns

**Server Properties Editing**
The create server wizard includes a TextArea (step 4) where users can edit server.properties:
- Default properties are generated with common Minecraft settings
- Properties are parsed from text format into a dictionary
- The parser handles comments, empty lines, booleans, integers, and strings
- Parsed properties are stored in `ServerConfig.server_properties` dictionary

**Async/Await with PyDo**
The PyDo client is synchronous but we're in an async Textual app. All PyDo calls must use:
```python
resp = await asyncio.to_thread(self.client.droplets.get, droplet_id)
```

**SSH Key Matching**
When checking if SSH key exists in DigitalOcean, compare only key type and data (not comments):
```python
local_key_type = key_parts[0]  # e.g., "ssh-ed25519"
local_key_data = key_parts[1]  # The actual key data
# Ignore key_parts[2] which is the comment
```

**SSH Key Validation**
The SSH key selector only shows public keys that have matching private keys:
- Scans `~/.ssh/*.pub` files
- For each public key, checks if private key exists (same name without `.pub`)
- Only displays keys with both public and private key files
- Validates private key exists before SSH connection
- Provides clear error if private key is missing

**Progress Streaming**
Installation progress uses callbacks that receive line-by-line output from SSH commands:
```python
def progress_callback(line: str):
    self.query_one(ProgressLog).add_line(line)

await installer.install(progress_callback=progress_callback)
```

**Systemd Service Creation**
All Minecraft servers are installed as systemd services for automatic management:
- Service name: `minecraft-server.service`
- Working directory: `/opt/minecraft`
- Automatic restart on failure
- Controls: `systemctl start/stop/restart minecraft-server`

## Testing Notes

- Use pytest with `asyncio_mode = "auto"` (configured in pyproject.toml)
- Mock DigitalOcean API calls in tests using pytest fixtures
- Test SSH operations should mock paramiko connections
- Settings can be overridden in tests by passing kwargs to `Settings()`

## Key Bindings

The TUI supports vi-style key bindings for navigation:

**Global Bindings (all screens):**
- `q`: Quit application
- `d`: Toggle dark/light mode
- `j`: Move focus to next widget / Move down in lists
- `k`: Move focus to previous widget / Move up in lists

**Server List Screen:**
- `j`/`k`: Navigate up/down through server list
- `g`: Jump to top of list
- `G`: Jump to bottom of list
- `Enter`: Select server to view details

**Radio Button Selection:**
- `j`: Move to next radio button option
- `k`: Move to previous radio button option
- `Space` or `Enter`: Select the focused option

**Navigation:**
- Tab/Shift+Tab also work for focus cycling
- Arrow keys work for all navigation
- Enter to activate buttons/selections
- Escape to go back (when applicable)

## Configuration

Required environment variable:
- `DIGITALOCEAN_TOKEN`: DigitalOcean API token (required for all operations)

Optional environment variables with defaults:
- `DEFAULT_REGION=nyc3`: DigitalOcean region
- `DEFAULT_SIZE=s-2vcpu-4gb`: Droplet size (minimum 2GB RAM for Minecraft)
- `DEFAULT_IMAGE=ubuntu-24-04-x64`: Ubuntu image
- `SSH_KEY_PATH=~/.ssh/id_rsa.pub`: SSH public key path
- `SSH_PRIVATE_KEY_PATH=~/.ssh/id_rsa`: SSH private key path
- `DEFAULT_JAVA_VERSION=21`: Java version for Minecraft

## Dependencies

Core runtime:
- `textual`: TUI framework
- `pydo`: DigitalOcean API client (synchronous, wrap with `asyncio.to_thread`)
- `paramiko`: SSH client for remote installation and log retrieval
- `mcrcon`: Minecraft RCON client (synchronous, wrap with `asyncio.to_thread`)
- `pyfiglet`: ASCII art generator for splash screen
- `pydantic` + `pydantic-settings`: Configuration and validation

Development:
- `pytest` + `pytest-asyncio` + `pytest-cov`: Testing
- `ruff`: Linting and formatting
- `textual-dev`: Development tools (console, run, etc.)

## UI Layout

The application uses a full-screen responsive layout:
- All screens expand to fill the entire terminal (100% width and height)
- Uses Textual's fractional units (`1fr`) for flexible sizing
- DataTable and TextArea widgets expand to fill available space
- The only centered modal is the delete confirmation dialog (60% width, max 80 columns)
- All main containers have `overflow-y: auto` for scrolling long content
- Buttons use their natural width (not stretched to 100%) for a cleaner look

## Server Console & RCON

The TUI includes a live server console accessible from the server detail screen:
- **RCON Integration**: Uses Minecraft's RCON protocol (port 25575) for remote console access
- **Automatic Password Retrieval**: Securely retrieves RCON password from server.properties via SSH
- **Live Command Execution**: Send Minecraft commands (list, say, tp, etc.) from the TUI
- **Server Logs**: View recent server logs from systemd journal
- **Real-time Responses**: See command output immediately in the console

RCON is automatically enabled in server.properties with a secure random password.

## Security Features

All droplets are automatically hardened via cloud-init:
- **fail2ban**: Protects against SSH brute force attacks (3 max retries, 30-minute ban)
- **UFW Firewall**: Default deny incoming, only SSH (22), Minecraft (25565), and RCON (25575) allowed
- **SSH Hardening**: Root password login disabled, SSH key authentication only
- **Minecraft DDoS Protection**: Optional fail2ban filter for connection spam

## Common Gotchas

1. **PyDo is synchronous**: Always wrap PyDo calls with `asyncio.to_thread()` in async functions
2. **SSH key comments**: When comparing SSH keys, ignore the comment part (third field)
3. **Droplet activation**: New droplets take 30-60 seconds to become active, cloud-init takes another 60 seconds
4. **Server properties**: Boolean values must be lowercase strings ("true"/"false") in server.properties
5. **EULA acceptance**: Must set `accept_eula=True` in ServerConfig or server won't start
6. **Screen sizing**: Don't use fixed widths - use 100% or fractional units for responsive layout
7. **Cloud-init timing**: Wait at least 60 seconds after droplet activation for cloud-init to complete security setup
