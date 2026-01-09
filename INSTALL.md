# Installation Guide

Complete installation instructions for the MCP Multi-Agent Game League System.

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [Method 1: UV (Recommended)](#method-1-uv-recommended)
  - [Method 2: Pip from PyPI](#method-2-pip-from-pypi)
  - [Method 3: From Source](#method-3-from-source)
  - [Method 4: Docker](#method-4-docker)
- [Verification](#verification)
- [Development Installation](#development-installation)
- [Optional Dependencies](#optional-dependencies)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **Python** | 3.11+ | 3.12+ |
| **RAM** | 2 GB | 4 GB+ |
| **Disk Space** | 500 MB | 1 GB+ |
| **OS** | Linux, macOS, Windows | Linux/macOS |

### Required Software

```bash
# Check Python version
python --version  # Should be 3.11 or higher

# Install UV (recommended package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

---

## Installation Methods

### Method 1: UV (Recommended)

**UV** is the fastest Python package manager and is recommended for this project.

#### Step 1: Install UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

#### Step 2: Install the Package

```bash
# Install from PyPI (when published)
uv pip install mcp-game-league

# Or install with all optional dependencies
uv pip install "mcp-game-league[dev,llm]"
```

#### Step 3: Verify Installation

```bash
mcp-version
```

**Expected Output:**
```
mcp-game-league v2.0.0
Production-Grade MCP Multi-Agent Game League System

Certifications:
  • ISO_IEC_25010: 100% Certified
  • MIT_LEVEL: Highest Level
  • TEST_COVERAGE: 86.22%
  • TESTS_PASSED: 1605+

License: MIT
Homepage: https://github.com/mcp-game/mcp-multi-agent-game
```

---

### Method 2: Pip from PyPI

Standard installation using pip.

```bash
# Basic installation
pip install mcp-game-league

# With optional dependencies
pip install "mcp-game-league[dev,llm]"

# Upgrade to latest version
pip install --upgrade mcp-game-league
```

---

### Method 3: From Source

For development or to get the latest unreleased features.

#### Using UV (Recommended)

```bash
# Clone the repository
git clone https://github.com/mcp-game/mcp-multi-agent-game.git
cd mcp-multi-agent-game

# Install with UV
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows

# Verify installation
python -m src.cli --help
```

#### Using Pip

```bash
# Clone the repository
git clone https://github.com/mcp-game/mcp-multi-agent-game.git
cd mcp-multi-agent-game

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install in editable mode
pip install -e .

# Or with development dependencies
pip install -e ".[dev,llm]"
```

---

### Method 4: Docker

Run the system in a containerized environment.

#### Quick Start

```bash
# Pull the image (when published)
docker pull mcpgame/mcp-game-league:latest

# Run the full system
docker-compose up
```

#### Build from Source

```bash
# Clone repository
git clone https://github.com/mcp-game/mcp-multi-agent-game.git
cd mcp-multi-agent-game

# Build image
docker build -t mcp-game-league:local .

# Run with docker-compose
docker-compose up
```

#### Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  league-manager:
    image: mcp-game-league:latest
    command: mcp-league --dashboard
    ports:
      - "8000:8000"
      - "8050:8050"
    environment:
      - LOG_LEVEL=INFO

  referee:
    image: mcp-game-league:latest
    command: mcp-referee --port 8001
    ports:
      - "8001:8001"

  player1:
    image: mcp-game-league:latest
    command: mcp-player --port 8101 --strategy adaptive
    ports:
      - "8101:8101"
```

---

## Verification

### Test Your Installation

```bash
# Check version
mcp-version

# Display help
mcp-game --help

# Run a quick test
mcp-game league --help
```

### Run First Tournament

```bash
# Start League Manager with dashboard
mcp-league --dashboard

# In another terminal, start a player
mcp-player --port 8101 --strategy random

# In another terminal, start another player
mcp-player --port 8102 --strategy adaptive
```

Then visit: http://localhost:8050

---

## Development Installation

For contributors and developers.

### Step 1: Clone and Setup

```bash
# Clone repository
git clone https://github.com/mcp-game/mcp-multi-agent-game.git
cd mcp-multi-agent-game

# Install with UV (recommended)
uv sync

# Or with pip
pip install -e ".[dev]"
```

### Step 2: Install Pre-commit Hooks

```bash
# Install pre-commit
uv pip install pre-commit

# Setup hooks
pre-commit install
```

### Step 3: Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m "not slow"  # Skip slow tests
pytest -m integration  # Only integration tests
```

### Step 4: Code Quality Checks

```bash
# Linting
ruff check src/

# Type checking
mypy src/

# Format code
ruff format src/
```

---

## Optional Dependencies

### LLM Support

For AI-powered strategies using Claude or GPT.

```bash
# Install LLM dependencies
uv pip install "mcp-game-league[llm]"

# Set API keys
export ANTHROPIC_API_KEY="your-key-here"
export OPENAI_API_KEY="your-key-here"

# Run with LLM strategy
mcp-player --strategy llm --model claude-3-sonnet
```

### Development Tools

```bash
# Install all development dependencies
uv pip install "mcp-game-league[dev]"

# Includes:
# - pytest, pytest-asyncio, pytest-cov
# - ruff, mypy
# - pre-commit
# - bandit (security)
```

---

## Troubleshooting

### Common Issues

#### Issue: Python Version Too Old

```bash
# Error: requires-python >=3.11

# Solution: Install Python 3.11+
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11

# Windows
# Download from python.org
```

#### Issue: UV Not Found

```bash
# Error: command not found: uv

# Solution: Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (if needed)
export PATH="$HOME/.cargo/bin:$PATH"
```

#### Issue: Port Already in Use

```bash
# Error: Address already in use: 8000

# Solution: Use different port
mcp-league --port 8010

# Or kill existing process
lsof -ti:8000 | xargs kill -9
```

#### Issue: Module Not Found

```bash
# Error: ModuleNotFoundError: No module named 'src'

# Solution: Install in editable mode
pip install -e .

# Or activate virtual environment
source .venv/bin/activate
```

#### Issue: Permission Denied

```bash
# Error: Permission denied

# Solution: Use user install
pip install --user mcp-game-league

# Or use virtual environment
python -m venv venv
source venv/bin/activate
pip install mcp-game-league
```

---

## Platform-Specific Notes

### macOS

```bash
# Install Xcode Command Line Tools (if needed)
xcode-select --install

# Install Python via Homebrew
brew install python@3.11

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Linux (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install Python 3.11+
sudo apt install python3.11 python3.11-venv python3-pip

# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows

```powershell
# Install Python from python.org
# Download: https://www.python.org/downloads/

# Install UV
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or use pip
pip install uv
```

---

## Uninstallation

```bash
# Using pip
pip uninstall mcp-game-league

# Using UV
uv pip uninstall mcp-game-league

# Remove configuration (optional)
rm -rf ~/.mcp-game/
```

---

## Next Steps

After installation:

1. 📖 Read the [Quick Start Guide](README.md#-quick-start-5-minutes-to-first-tournament)
2. 🏗️ Explore [MCP Architecture](README.md#-mcp-architecture--real-time-communication)
3. 🎮 Run your [First Tournament](README.md#-operating-the-system)
4. 🔬 Study [MIT Innovations](README.md#-mit-level-innovations)
5. 👨‍💻 Check [Contributing Guide](CONTRIBUTING.md)

---

## Support

- **Documentation**: https://github.com/mcp-game/mcp-multi-agent-game#readme
- **Issues**: https://github.com/mcp-game/mcp-multi-agent-game/issues
- **Discussions**: https://github.com/mcp-game/mcp-multi-agent-game/discussions
- **Email**: mcp-game@example.com

---

## License

MIT License - see [LICENSE](LICENSE) file for details.
