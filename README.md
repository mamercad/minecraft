# Minecraft Server Manager TUI

A beautiful terminal user interface (TUI) for managing Minecraft servers on DigitalOcean droplets.

## Features

- **Easy Setup**: Simple onboarding with `$DIGITALOCEAN_TOKEN` environment variable
- **Multiple Server Types**: Support for Vanilla, Forge, and custom modpack servers
- **Automated Deployment**: Automatically provisions DigitalOcean droplets and installs Minecraft
- **Server Management**: Start, stop, restart, and delete servers from the TUI
- **Real-time Progress**: Stream installation progress with live updates

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
   - Configure server settings
   - Accept the Minecraft EULA
   - Watch as your server is created!

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
│       └── server_card.py
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
2. **SSH Key Upload**: Your SSH public key is automatically uploaded to DigitalOcean
3. **Server Installation**: The app connects via SSH and runs installation scripts
4. **Systemd Service**: A systemd service is created for automatic server management
5. **Tag Management**: Droplets are tagged with `minecraft-tui` for easy identification

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

## Security Notes

- **Never commit your DigitalOcean token** - use environment variables
- **SSH keys are never logged** - your private keys stay local
- **Tokens are stored securely** - using Pydantic's `SecretStr`
- **Droplet firewall** - configure UFW to restrict access (optional)

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
