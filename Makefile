# MCP Multi-Agent Game League - Makefile
# Usage: make <target>

.PHONY: help setup install dev test lint format run run-league clean docker docker-up docker-down

# Default target
help:
	@echo "MCP Multi-Agent Game League"
	@echo "============================"
	@echo ""
	@echo "Available targets:"
	@echo "  setup       - Install UV and setup project"
	@echo "  install     - Install dependencies with UV"
	@echo "  dev         - Install with dev dependencies"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linter (ruff)"
	@echo "  format      - Format code (ruff)"
	@echo "  typecheck   - Run type checker (mypy)"
	@echo "  run         - Start all components"
	@echo "  run-league  - Run a full league with 4 players"
	@echo "  clean       - Clean build artifacts"
	@echo "  docker      - Build Docker image"
	@echo "  docker-up   - Start with Docker Compose"
	@echo "  docker-down - Stop Docker Compose"

# Setup
setup:
	@./scripts/setup.sh

install:
	uv sync

dev:
	uv sync --all-extras

# Testing & Quality
test:
	uv run pytest tests/ -v --cov=src --cov-report=term-missing

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/
	uv run ruff check src/ tests/ --fix

typecheck:
	uv run mypy src/

# Running
run:
	uv run python -m src.main

run-league:
	uv run python -m src.main --run --players 4

run-debug:
	uv run python -m src.main --run --players 4 --debug

# Components
run-league-manager:
	uv run python -m src.main --component league

run-referee:
	uv run python -m src.main --component referee

run-player:
	@read -p "Player name: " name; \
	read -p "Port (default 8101): " port; \
	uv run python -m src.main --component player --name "$$name" --port $${port:-8101} --register

# Clean
clean:
	rm -rf .venv
	rm -rf __pycache__
	rm -rf src/__pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Docker
docker:
	docker build -t mcp-game-league .

docker-dev:
	docker build --target development -t mcp-game-league:dev .

docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

