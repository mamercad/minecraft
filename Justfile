# List available recipes
default:
    @just --list

# Install dependencies
install:
    uv sync

# Run the application
run:
    uv run minecraft-tui

# Run tests
test:
    uv run pytest

# Run tests with coverage
test-cov:
    uv run pytest --cov=src/minecraft_tui --cov-report=html
    @echo "Coverage report generated in htmlcov/index.html"

# Run linting checks
lint:
    uv run ruff check .

# Format code
format:
    uv run ruff format .

# Fix linting issues automatically
fix:
    uv run ruff check --fix .

# Clean up generated files
clean:
    rm -rf .pytest_cache
    rm -rf htmlcov
    rm -rf .coverage
    rm -rf .ruff_cache
    rm -rf dist
    rm -rf build
    rm -rf *.egg-info
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete

# Run Textual development console
dev-console:
    textual console

# Install, format, lint, and test
all: install format lint test
