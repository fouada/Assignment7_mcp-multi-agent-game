# Command Reference Guide

This document provides a complete reference for operating and executing the MCP Multi-Agent Game League system based on the Even/Odd game protocol specification.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [CLI Command Reference](#cli-command-reference)
5. [Running Modes](#running-modes)
6. [Component Configuration](#component-configuration)
7. [Port Mapping](#port-mapping)
8. [Environment Variables](#environment-variables)
9. [Makefile Commands](#makefile-commands)
10. [Docker Commands](#docker-commands)
11. [Protocol Specification](#protocol-specification)
12. [Agent Lifecycle](#agent-lifecycle)
13. [Timeouts Configuration](#timeouts-configuration)
14. [Error Codes](#error-codes)
15. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | Python 3.11+ recommended |
| UV | Latest | Package manager (recommended) |
| pip | Latest | Alternative to UV |
| Docker | 20.10+ | Optional, for containerized deployment |
| Docker Compose | 2.0+ | Optional, for multi-container setup |

### Operating System Support

- Linux (Ubuntu 20.04+, Debian 11+)
- macOS (12.0+)
- Windows (WSL2 recommended)

---

## Installation

### Option 1: Using UV (Recommended)

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
cd Assignment_7_MCP_Multi_Agent_Game

# Run setup script
./scripts/setup.sh

# Or manual install with all extras
uv sync --all-extras
```

### Option 2: Using pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install with development dependencies
pip install -e ".[dev,llm]"
```

### Verify Installation

```bash
# Using UV
uv run python -c "import src; print('Installation successful!')"

# Using pip
python -c "import src; print('Installation successful!')"
```

---

## Quick Start

### Fastest Way to Run the League

```bash
# Start a complete league with 4 players using random/pattern strategies
uv run python -m src.main --run --players 4

# Start with LLM (Claude) strategy - requires API key
export ANTHROPIC_API_KEY=your-key-here
uv run python -m src.main --run --players 4 --strategy llm
```

---

## CLI Command Reference

### Main Entry Point

```bash
python -m src.main [OPTIONS]
```

### Global Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--component` | choice | `all` | Component to start: `league`, `referee`, `player`, `all` |
| `--name` | string | `Player` | Name for player component |
| `--port` | integer | auto | Port number for the component |
| `--players` | integer | `4` | Number of players for full league mode |
| `--strategy` | choice | `mixed` | Player strategy: `mixed`, `random`, `pattern`, `llm` |
| `--llm-provider` | choice | `anthropic` | LLM provider: `anthropic`, `openai` |
| `--llm-model` | string | auto | LLM model name (e.g., `claude-sonnet-4-20250514`) |
| `--run` | flag | false | Run the league automatically |
| `--register` | flag | false | Auto-register player with league |
| `--debug` | flag | false | Enable debug logging |

### Strategy Types

| Strategy | Description | LLM Required |
|----------|-------------|--------------|
| `mixed` | Alternates between random and pattern | No |
| `random` | Purely random number selection (1-5) | No |
| `pattern` | Pattern-based selection strategy | No |
| `llm` | AI-powered strategy using Claude/GPT | Yes |

---

## Running Modes

### Mode 1: Full League (Automatic)

Starts all components and runs the complete tournament automatically.

```bash
# Basic execution with 4 players
uv run python -m src.main --run --players 4

# With debug logging
uv run python -m src.main --run --players 4 --debug

# With 6 players
uv run python -m src.main --run --players 6

# With LLM strategy
uv run python -m src.main --run --players 4 --strategy llm
```

**What happens:**
1. League Manager starts on port 8000
2. Referee starts on port 8001
3. N players start on ports 8101-81XX
4. All players auto-register
5. Round-robin schedule is generated
6. All matches are executed
7. Final standings are displayed

### Mode 2: Manual (Multi-Terminal)

Start each component separately for testing or development.

**Terminal 1 - Start League Manager:**
```bash
uv run python -m src.main --component league
# Starts on http://localhost:8000/mcp
```

**Terminal 2 - Start Referee:**
```bash
uv run python -m src.main --component referee
# Starts on http://localhost:8001/mcp
```

**Terminal 3 - Start Player 1:**
```bash
uv run python -m src.main --component player --name "AlphaBot" --port 8101 --register
```

**Terminal 4 - Start Player 2:**
```bash
uv run python -m src.main --component player --name "BetaBot" --port 8102 --register
```

**Terminal 5 - Start Player 3:**
```bash
uv run python -m src.main --component player --name "GammaBot" --port 8103 --register
```

**Terminal 6 - Start Player 4:**
```bash
uv run python -m src.main --component player --name "DeltaBot" --port 8104 --register
```

### Mode 3: Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Run in detached mode
docker-compose up --build -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f league_manager
docker-compose logs -f referee
docker-compose logs -f player1

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

---

## Component Configuration

### League Manager Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| Host | `localhost` | Bind address |
| Port | `8000` | Listen port |
| Endpoint | `/mcp` | MCP endpoint path |
| Min Players | `2` | Minimum players to start |
| Max Players | `100` | Maximum players allowed |

### Referee Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| Host | `localhost` | Bind address |
| Port | `8001` | Listen port |
| Endpoint | `/mcp` | MCP endpoint path |
| Move Timeout | `30s` | Timeout for player moves |

### Player Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| Host | `localhost` | Bind address |
| Port | `8101+` | Listen port (incrementing) |
| Endpoint | `/mcp` | MCP endpoint path |
| Strategy | `random` | Default strategy |

---

## Port Mapping

### Standard Port Assignments

| Component | Port | URL |
|-----------|------|-----|
| League Manager | 8000 | `http://localhost:8000/mcp` |
| Referee | 8001 | `http://localhost:8001/mcp` |
| Player 1 | 8101 | `http://localhost:8101/mcp` |
| Player 2 | 8102 | `http://localhost:8102/mcp` |
| Player 3 | 8103 | `http://localhost:8103/mcp` |
| Player 4 | 8104 | `http://localhost:8104/mcp` |
| Player N | 81XX | `http://localhost:81XX/mcp` |

### Port Formula for Players

```
Player Port = 8100 + Player_Number
Example: Player 5 = 8105
```

---

## Environment Variables

### Required for LLM Strategy

```bash
# For Anthropic Claude
export ANTHROPIC_API_KEY=your-anthropic-key

# For OpenAI GPT
export OPENAI_API_KEY=your-openai-key
```

### Optional Configuration

```bash
# Logging level (DEBUG, INFO, WARNING, ERROR)
export LOG_LEVEL=INFO

# Server configuration
export LEAGUE_HOST=localhost
export LEAGUE_PORT=8000
export REFEREE_HOST=localhost
export REFEREE_PORT=8001

# Timeouts (in seconds)
export MOVE_TIMEOUT_SECONDS=30
export MATCH_TIMEOUT_SECONDS=300

# Security
export SECRET_KEY=your-secret-key-here
```

### Using .env File

Create a `.env` file in the project root:

```bash
# .env
LOG_LEVEL=INFO
ANTHROPIC_API_KEY=sk-ant-your-key
OPENAI_API_KEY=sk-your-key
LEAGUE_HOST=localhost
LEAGUE_PORT=8000
REFEREE_PORT=8001
```

---

## Makefile Commands

### Quick Reference

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make setup` | Install UV and setup project |
| `make install` | Install dependencies with UV |
| `make dev` | Install with dev dependencies |
| `make run` | Start all components (interactive) |
| `make run-league` | Run full league with 4 players |
| `make run-debug` | Run with debug logging |
| `make test` | Run all tests |
| `make lint` | Run linter (ruff) |
| `make format` | Format code (ruff) |
| `make typecheck` | Run type checker (mypy) |
| `make clean` | Clean build artifacts |
| `make docker` | Build Docker image |
| `make docker-up` | Start with Docker Compose |
| `make docker-down` | Stop Docker Compose |
| `make docker-logs` | View Docker logs |

### Component-Specific Commands

```bash
# Start league manager only
make run-league-manager

# Start referee only
make run-referee

# Start a player (interactive prompt)
make run-player
```

---

## Docker Commands

### Building Images

```bash
# Build production image
docker build -t mcp-game-league .

# Build development image
docker build --target development -t mcp-game-league:dev .
```

### Running Containers

```bash
# Run league manager
docker run -p 8000:8000 -e LOG_LEVEL=INFO mcp-game-league \
  python -m src.main --component league

# Run referee
docker run -p 8001:8001 -e LOG_LEVEL=INFO mcp-game-league \
  python -m src.main --component referee

# Run player
docker run -p 8101:8101 -e LOG_LEVEL=INFO mcp-game-league \
  python -m src.main --component player --name "Bot1" --port 8101 --register
```

### Docker Compose Commands

```bash
# Start all services (build if needed)
docker-compose up --build

# Start in background
docker-compose up -d

# Scale players
docker-compose up --scale player1=1 --scale player2=1 -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Remove volumes
docker-compose down -v

# Restart specific service
docker-compose restart league_manager
```

---

## Protocol Specification

### Message Envelope Structure

Every protocol message follows this envelope format:

```json
{
  "protocol": "league.v1",
  "message_type": "MESSAGE_TYPE",
  "league_id": "league_2024_01",
  "conversation_id": "uuid-v4",
  "timestamp": "2024-12-13T10:00:00.000Z",
  "sender": {
    "agent_type": "player|referee|league_manager",
    "agent_id": "P01|REF01|LM01"
  },
  "auth_token": "jwt-token-here",
  "payload": {}
}
```

### Message Types

#### Registration Messages

| Type | Direction | Description |
|------|-----------|-------------|
| `REFEREE_REGISTER_REQUEST` | Referee -> League Manager | Register referee |
| `REFEREE_REGISTER_RESPONSE` | League Manager -> Referee | Registration result |
| `LEAGUE_REGISTER_REQUEST` | Player -> League Manager | Register player |
| `LEAGUE_REGISTER_RESPONSE` | League Manager -> Player | Registration result with token |

#### Game Flow Messages

| Type | Direction | Description |
|------|-----------|-------------|
| `MATCH_ASSIGN` | League Manager -> Referee | Assign match to referee |
| `GAME_INVITE` | Referee -> Player | Invite player to match |
| `GAME_ACCEPT` | Player -> Referee | Accept game invitation |
| `GAME_START` | Referee -> Player | Game is starting |
| `MOVE_REQUEST` | Referee -> Player | Request move from player |
| `MOVE_RESPONSE` | Player -> Referee | Player's move response |
| `ROUND_RESULT` | Referee -> Player | Result of round |
| `GAME_END` | Referee -> Player | Game finished |
| `MATCH_RESULT` | Referee -> League Manager | Match result |
| `STANDINGS_UPDATE` | League Manager -> All | Updated standings |

### JSON-RPC 2.0 Format

All messages are wrapped in JSON-RPC 2.0:

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {
      "protocol": "league.v1",
      "message_type": "MOVE_RESPONSE",
      "move": 3
    }
  }
}
```

### Response Format

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {
    "success": true,
    "data": {}
  }
}
```

---

## Agent Lifecycle

### Player Agent States

| State | Description | Transitions |
|-------|-------------|-------------|
| `INIT` | Agent created | -> REGISTERED, -> INIT (retry) |
| `REGISTERED` | Registered with league | -> ACTIVE, -> SUSPENDED |
| `ACTIVE` | Ready for matches | -> IN_GAME, -> REGISTERED |
| `IN_GAME` | Currently playing | -> ACTIVE, -> SUSPENDED |
| `SUSPENDED` | Temporarily unavailable | -> REGISTERED, -> SHUTDOWN |
| `SHUTDOWN` | Shutting down | -> (terminated) |

### Referee Agent States

| State | Description | Transitions |
|-------|-------------|-------------|
| `INIT` | Agent created | -> READY |
| `READY` | Waiting for match | -> MANAGING_MATCH |
| `MANAGING_MATCH` | Match assigned | -> WAITING_ACCEPTS |
| `WAITING_ACCEPTS` | Waiting for players | -> GAME_RUNNING, -> READY (timeout) |
| `GAME_RUNNING` | Game in progress | -> WAITING_MOVES |
| `WAITING_MOVES` | Waiting for moves | -> RESOLVING_ROUND |
| `RESOLVING_ROUND` | Processing round | -> GAME_RUNNING, -> REPORTING_RESULT |
| `REPORTING_RESULT` | Sending results | -> READY |
| `SHUTDOWN` | Shutting down | -> (terminated) |

### League Manager States

| State | Description | Transitions |
|-------|-------------|-------------|
| `INIT` | League created | -> REGISTRATION_OPEN |
| `REGISTRATION_OPEN` | Accepting players | -> READY |
| `READY` | Minimum players reached | -> RUNNING |
| `RUNNING` | League active | -> ROUND_IN_PROGRESS |
| `ROUND_IN_PROGRESS` | Round being played | -> BETWEEN_ROUNDS |
| `BETWEEN_ROUNDS` | Round completed | -> ROUND_IN_PROGRESS, -> COMPLETE |
| `COMPLETE` | All rounds done | -> SHUTDOWN |
| `SHUTDOWN` | Shutting down | -> (terminated) |

---

## Timeouts Configuration

### Default Timeout Values

| Timeout | Default | Description |
|---------|---------|-------------|
| Move Timeout | 30 seconds | Time for player to submit move |
| Match Timeout | 300 seconds | Total time for a match |
| Registration Timeout | 60 seconds | Time to complete registration |
| Connection Timeout | 5 seconds | HTTP connection timeout |
| Request Timeout | 30 seconds | HTTP request timeout |

### Retry Policy

| Parameter | Default | Description |
|-----------|---------|-------------|
| Max Retries | 3 | Maximum retry attempts |
| Base Delay | 1 second | Initial backoff delay |
| Max Delay | 30 seconds | Maximum backoff delay |
| Backoff Multiplier | 2 | Exponential backoff factor |

### Configuring Timeouts

**In config/servers.json:**
```json
{
  "game": {
    "move_timeout": 30.0,
    "rounds_per_match": 5
  },
  "retry": {
    "max_retries": 3,
    "base_delay": 1.0,
    "max_delay": 30.0
  }
}
```

**Via Environment:**
```bash
export MOVE_TIMEOUT_SECONDS=30
export MATCH_TIMEOUT_SECONDS=300
```

---

## Error Codes

### League Error Codes

| Code | Name | Description |
|------|------|-------------|
| `L001` | LEAGUE_FULL | Maximum players reached |
| `L002` | INVALID_TOKEN | Authentication token invalid |
| `L003` | PLAYER_NOT_FOUND | Player ID not found |
| `L004` | LEAGUE_NOT_STARTED | League has not started |
| `L005` | LEAGUE_ALREADY_STARTED | League already in progress |
| `L006` | REGISTRATION_CLOSED | Registration period ended |

### Game Error Codes

| Code | Name | Description |
|------|------|-------------|
| `G001` | INVALID_MOVE | Move value out of range (1-5) |
| `G002` | MOVE_TIMEOUT | Player did not respond in time |
| `G003` | PLAYER_DISCONNECTED | Player connection lost |
| `G004` | GAME_NOT_FOUND | Game ID not found |
| `G005` | NOT_YOUR_TURN | Out of turn move attempt |
| `G006` | GAME_ALREADY_ENDED | Game has finished |

### JSON-RPC Error Codes

| Code | Description |
|------|-------------|
| `-32700` | Parse error |
| `-32600` | Invalid Request |
| `-32601` | Method not found |
| `-32602` | Invalid params |
| `-32603` | Internal error |

---

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use a different port
uv run python -m src.main --component league --port 9000
```

#### Connection Refused

1. **Check if service is running:**
```bash
curl http://localhost:8000/health
```

2. **Check logs:**
```bash
# Docker
docker-compose logs league_manager

# Local
# Check terminal output
```

3. **Verify network:**
```bash
# Docker network
docker network ls
docker network inspect mcp-game_default
```

#### Protocol Version Mismatch

Ensure all components use the same protocol version:
```json
{
  "protocol": "league.v1"
}
```

#### LLM Strategy Not Working

1. **Check API key is set:**
```bash
echo $ANTHROPIC_API_KEY
# or
echo $OPENAI_API_KEY
```

2. **Verify provider selection:**
```bash
uv run python -m src.main --run --players 4 --strategy llm --llm-provider anthropic
```

3. **Check for API errors in logs:**
```bash
uv run python -m src.main --run --players 4 --strategy llm --debug
```

### Debug Mode

Enable debug logging for detailed output:

```bash
# Via flag
uv run python -m src.main --run --players 4 --debug

# Via environment
LOG_LEVEL=DEBUG uv run python -m src.main --run --players 4

# In Docker
docker-compose up -e LOG_LEVEL=DEBUG
```

### Health Checks

Each component exposes a health endpoint:

```bash
# League Manager
curl http://localhost:8000/health

# Referee
curl http://localhost:8001/health

# Player
curl http://localhost:8101/health
```

### Log Locations

| Deployment | Log Location |
|------------|--------------|
| Local | stdout/stderr |
| Docker | `docker-compose logs` |
| Systemd | `journalctl -u mcp-league` |

---

## Game Rules: Even/Odd

### Overview

- Two players compete in a match
- One player is assigned "ODD", the other "EVEN"
- Each player chooses a number from 1-5
- If the sum is odd, ODD player wins the round
- If the sum is even, EVEN player wins the round
- Best of N rounds determines match winner

### Scoring System

| Match Result | League Points |
|--------------|---------------|
| Win | 3 points |
| Draw | 1 point |
| Loss | 0 points |

### Round-Robin Format

For N players, total matches = N * (N-1) / 2

| Players | Total Matches |
|---------|---------------|
| 2 | 1 |
| 4 | 6 |
| 6 | 15 |
| 8 | 28 |

---

## Testing

### Run All Tests

```bash
# Using UV
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=src --cov-report=html

# Or use Makefile
make test
```

### Run Specific Tests

```bash
# Test game logic
uv run pytest tests/test_game.py -v

# Test protocol
uv run pytest tests/test_protocol.py -v

# Test transport
uv run pytest tests/test_transport.py -v
```

---

## References

- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [UV Package Manager](https://docs.astral.sh/uv/)

---

*Last Updated: December 2024*

