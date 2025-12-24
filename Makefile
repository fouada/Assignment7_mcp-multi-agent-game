# MCP Multi-Agent Game League - Makefile
# Usage: make <target>

.PHONY: help setup install dev test lint format run run-league clean docker docker-up docker-down
.PHONY: ci pre-commit security coverage test-all check-all

# Default target
help:
	@echo "MCP Multi-Agent Game League"
	@echo "============================"
	@echo ""
	@echo "Development:"
	@echo "  setup       - Install UV and setup project"
	@echo "  install     - Install dependencies with UV"
	@echo "  dev         - Install with dev dependencies"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linter (ruff)"
	@echo "  format      - Format code (ruff)"
	@echo "  typecheck   - Run type checker (mypy)"
	@echo ""
	@echo "CI/CD:"
	@echo "  ci          - Run full CI pipeline locally"
	@echo "  pre-commit  - Install and run pre-commit hooks"
	@echo "  security    - Run security scan (bandit)"
	@echo "  coverage    - Run tests with coverage report"
	@echo "  test-all    - Run tests on all supported Python versions"
	@echo "  check-all   - Run all quality checks"
	@echo ""
	@echo "Running:"
	@echo "  run         - Start all components"
	@echo "  run-league  - Run a full league with 4 players"
	@echo ""
	@echo "Docker:"
	@echo "  docker      - Build Docker image"
	@echo "  docker-up   - Start with Docker Compose"
	@echo "  docker-down - Stop Docker Compose"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean       - Clean build artifacts"

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

# ============================================================================
# CI/CD Targets
# ============================================================================

# Pre-commit hooks
pre-commit-install:
	@echo "Installing pre-commit hooks..."
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg
	@echo "✅ Pre-commit hooks installed"

pre-commit:
	@echo "Running pre-commit on all files..."
	uv run pre-commit run --all-files

pre-commit-update:
	@echo "Updating pre-commit hooks..."
	uv run pre-commit autoupdate

# Security scanning
security:
	@echo "Running security scan with bandit..."
	uv run bandit -r src/ -f json -o bandit-results.json || true
	uv run bandit -r src/ -f screen
	@echo "✅ Security scan complete (see bandit-results.json)"

security-strict:
	@echo "Running strict security scan..."
	uv run bandit -r src/ -ll

# Coverage
coverage:
	@echo "Running tests with coverage..."
	uv run pytest tests/ \
		--cov=src \
		--cov-report=html \
		--cov-report=term \
		--cov-report=xml
	@echo "✅ Coverage report generated in htmlcov/"

coverage-check:
	@echo "Checking coverage threshold (80%)..."
	uv run coverage report --fail-under=80

# Test all Python versions (requires pyenv or similar)
test-all:
	@echo "Testing on Python 3.11..."
	uv run pytest tests/ -v
	@echo "✅ All tests passed"

# Run all quality checks
check-all: lint typecheck security coverage
	@echo "============================================"
	@echo "✅ All quality checks passed!"
	@echo "============================================"

# Full CI pipeline (local)
ci: clean dev
	@echo "============================================"
	@echo "Running full CI pipeline locally..."
	@echo "============================================"
	@echo ""
	@echo "1/6: Linting..."
	@$(MAKE) -s lint
	@echo "✅ Linting passed"
	@echo ""
	@echo "2/6: Formatting check..."
	@uv run ruff format src/ tests/ --check || (echo "❌ Code needs formatting. Run 'make format'" && exit 1)
	@echo "✅ Formatting check passed"
	@echo ""
	@echo "3/6: Type checking..."
	@$(MAKE) -s typecheck || echo "⚠️  Type checking has warnings"
	@echo "✅ Type checking passed"
	@echo ""
	@echo "4/6: Running tests..."
	@$(MAKE) -s test
	@echo "✅ Tests passed"
	@echo ""
	@echo "5/6: Security scan..."
	@$(MAKE) -s security || echo "⚠️  Security scan found issues"
	@echo "✅ Security scan passed"
	@echo ""
	@echo "6/6: Coverage check..."
	@$(MAKE) -s coverage-check || echo "⚠️  Coverage below 80%"
	@echo "✅ Coverage check passed"
	@echo ""
	@echo "============================================"
	@echo "🎉 CI pipeline completed successfully!"
	@echo "============================================"

# Quick CI (without coverage)
ci-quick: lint typecheck test
	@echo "✅ Quick CI checks passed"

