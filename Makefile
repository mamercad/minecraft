.PHONY: help install run test test-cov lint format fix clean dev-console

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv sync

run: ## Run the application
	uv run minecraft-tui

test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage
	uv run pytest --cov=src/minecraft_tui --cov-report=html
	@echo "Coverage report generated in htmlcov/index.html"

lint: ## Run linting checks
	uv run ruff check .

format: ## Format code
	uv run ruff format .

fix: ## Fix linting issues automatically
	uv run ruff check --fix .

clean: ## Clean up generated files
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf .ruff_cache
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

dev-console: ## Run Textual development console
	textual console

all: install format lint test ## Install, format, lint, and test
