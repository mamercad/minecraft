# Minecraft Server Manager TUI

A beautiful terminal user interface (TUI) for managing Minecraft servers on DigitalOcean droplets.

## Screenshots

![Main Menu](screenshots/main-menu.png)
*Main menu with Minecraft creeper ASCII art*

![Server Creation Wizard](screenshots/create-server.png)
*5-step server creation wizard with server.properties editor*

![Server List](screenshots/server-list.png)
*View and manage all your Minecraft servers*

![Server Console](screenshots/server-console.png)
*Live server console with RCON command support*

> **Note**: Screenshot generation coming soon. Use `Ctrl+S` in the app to capture screenshots.

## Features

- **Easy Setup**: Simple onboarding with `$DIGITALOCEAN_TOKEN` environment variable
- **Multiple Server Types**: Support for Vanilla, Forge, and custom modpack servers
- **Automated Deployment**: Automatically provisions DigitalOcean droplets and installs Minecraft
- **Security Hardening**: Automatic fail2ban, UFW firewall, and SSH key-only authentication
- **Server Management**: Start, stop, restart, and delete servers from the TUI
- **Live Server Console**: View logs and send commands via RCON directly from the TUI
- **Customizable Properties**: Edit server.properties in a built-in editor before deployment
- **Real-time Progress**: Stream installation progress with live updates
- **Vi Key Bindings**: Navigate with j/k keys for a familiar vim-like experience
- **Minecraft Themed UI**: Creeper ASCII art on splash screen (randomized each time) and main menu

## Requirements

- Python 3.11 or higher
- A DigitalOcean account with an API token
- SSH key at `~/.ssh/id_rsa.pub` (or configure a different path)

## Installation

### Using uv (recommended)

```bash
# Clone the repository
git clone https://github.com/mamercad/minecraft.git
cd minecraft

# Install dependencies
uv sync

# Run the application
uv run minecraft-tui
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/mamercad/minecraft.git
cd minecraft

# Create a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install the package
pip install -e .

# Run the application
minecraft-tui
```

## Quick Start

1. **Get a DigitalOcean API Token**:
   - Visit https://cloud.digitalocean.com/account/api/tokens
   - Create a new token with read/write access
   - Copy the token

2. **Set the Environment Variable**:
   ```bash
   export DIGITALOCEAN_TOKEN=your_token_here
   ```

3. **Run the Application**:
   ```bash
   minecraft-tui
   ```

4. **Create Your First Server**:
   - Select "Create New Server" from the main menu
   - Choose your server type (Vanilla, Forge, or Modpack)
   - Configure server settings (name, max players, region, droplet size)
   - Select your SSH key (only keys with matching private keys are shown)
   - Edit server.properties to customize gameplay (difficulty, gamemode, pvp, etc.)
   - Review your complete configuration including finalized server properties
   - Accept the Minecraft EULA and create!
   - Watch as your server is created!

## Key Bindings

The TUI supports both standard and vi-style key bindings:

**Navigation:**
- `j` / `Down Arrow` - Move down / focus next
- `k` / `Up Arrow` - Move up / focus previous
- `Tab` / `Shift+Tab` - Cycle through focusable elements
- `Enter` - Select / activate
- `q` - Quit application
- `d` - Toggle dark/light mode

**Server List:**
- `g` - Jump to top of list
- `G` - Jump to bottom of list
- Auto-refresh every 30 seconds (can be toggled off)

**Radio Buttons (Server Creation Wizard):**
- `j` - Move to next option
- `k` - Move to previous option
- `Space` / `Enter` - Select option

## Configuration

You can configure the application using environment variables or a `.env` file:

```bash
# Required
DIGITALOCEAN_TOKEN=your_token_here

# Optional (defaults shown)
DEFAULT_REGION=nyc3
DEFAULT_SIZE=s-2vcpu-4gb
DEFAULT_IMAGE=ubuntu-24-04-x64
SSH_KEY_PATH=~/.ssh/id_rsa.pub
SSH_PRIVATE_KEY_PATH=~/.ssh/id_rsa
DEFAULT_JAVA_VERSION=21
```

### Supported DigitalOcean Regions

Common regions include:
- `nyc1`, `nyc3` - New York
- `sfo3` - San Francisco
- `ams3` - Amsterdam
- `sgp1` - Singapore
- `lon1` - London
- `fra1` - Frankfurt
- `tor1` - Toronto

### Recommended Droplet Sizes

- `s-2vcpu-4gb` - Minimum for small servers (1-10 players)
- `s-4vcpu-8gb` - Better for modded servers or 10-20 players
- `s-8vcpu-16gb` - Large servers or heavy modpacks

## Project Structure

```
minecraft/
├── src/minecraft_tui/
│   ├── app.py                 # Main Textual application
│   ├── config.py              # Configuration management
│   ├── models/                # Data models
│   │   ├── server.py
│   │   └── droplet.py
│   ├── services/              # Backend services
│   │   ├── digitalocean.py    # DigitalOcean API wrapper
│   │   └── minecraft/         # Minecraft installers
│   │       ├── base.py
│   │       ├── vanilla.py
│   │       ├── forge.py
│   │       └── modpack.py
│   ├── screens/               # TUI screens
│   │   ├── welcome.py
│   │   ├── main_menu.py
│   │   ├── create_server.py
│   │   ├── server_list.py
│   │   └── server_detail.py
│   └── widgets/               # Custom widgets
│       ├── progress_log.py
│       ├── server_card.py
│       └── vi_radio_set.py
└── tests/                     # Unit tests
```

## Development

### Running Tests

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

# Fix linting issues
uv run ruff check --fix .
```

### Debugging

Use Textual's development console:

```bash
# Run with devtools
textual console

# In another terminal
uv run minecraft-tui
```

## How It Works

1. **Droplet Creation**: The app uses the DigitalOcean API (via `pydo`) to create a new droplet
2. **Security Hardening**: Cloud-init automatically configures fail2ban, UFW firewall, and SSH hardening
3. **SSH Key Upload**: Your SSH public key is automatically uploaded to DigitalOcean
4. **Server Installation**: The app connects via SSH and runs installation scripts
5. **Systemd Service**: A systemd service is created for automatic server management
6. **RCON Setup**: Remote console is automatically enabled with a secure password
7. **Tag Management**: Droplets are tagged with `minecraft-tui` for easy identification

## Server Console

Access your server console directly from the TUI:

1. Navigate to a running server in the server list
2. Click "View Console"
3. The TUI will:
   - Connect to your server via SSH
   - Retrieve the RCON password from server.properties
   - Establish an RCON connection
   - Display recent server logs
4. Send commands like:
   - `list` - Show online players
   - `say Hello everyone!` - Broadcast message
   - `time set day` - Change time of day
   - `weather clear` - Clear weather
   - `tp player1 player2` - Teleport players

All standard Minecraft commands are supported through RCON.

## Troubleshooting

### SSH Connection Issues

If you get SSH connection errors:

1. Ensure your SSH key exists at `~/.ssh/id_rsa.pub`
2. Check that the private key `~/.ssh/id_rsa` has correct permissions:
   ```bash
   chmod 600 ~/.ssh/id_rsa
   ```

### DigitalOcean API Errors

If you get API errors:

1. Verify your token is valid and has read/write access
2. Check your DigitalOcean account limits
3. Ensure the region and size are available in your account

### Server Installation Fails

If server installation fails:

1. Check the progress log for error messages
2. Verify the Minecraft version exists
3. For Forge servers, ensure the Forge version is compatible with the Minecraft version
4. For modpacks, verify the URL is accessible and the zip file is valid

## Security Features

All servers are automatically hardened on creation:

- **fail2ban Protection**: Automatically installed and configured
  - SSH brute force protection (3 max retries, 30-minute ban)
  - Optional Minecraft connection spam filter
- **UFW Firewall**: Pre-configured and enabled
  - Default deny incoming traffic
  - Only SSH (port 22), Minecraft (port 25565), and RCON (port 25575) allowed
- **RCON Security**: Randomly generated secure passwords for remote console access
- **SSH Hardening**: Root password login disabled, SSH keys only
- **Automatic Updates**: Cloud-init updates all packages on first boot

Additional security practices:

- **Never commit your DigitalOcean token** - use environment variables
- **SSH keys are never logged** - your private keys stay local
- **Tokens are stored securely** - using Pydantic's `SecretStr`

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass and code is formatted
6. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [Textual](https://textual.textualize.io/)
- DigitalOcean integration via [PyDo](https://github.com/digitalocean/pydo)
- Package management with [uv](https://github.com/astral-sh/uv)
