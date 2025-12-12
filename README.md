# 🎮 MCP Multi-Agent Game League

> **Production-Grade Model Context Protocol Based AI Game System**
>
> A sophisticated multi-agent game system implementing the Model Context Protocol (MCP) standard, featuring AI players competing in a round-robin league tournament, orchestrated by a referee agent.

<div align="center">

![Architecture](https://img.shields.io/badge/Architecture-3_Layer-blue)
![Protocol](https://img.shields.io/badge/Protocol-MCP_v1-green)
![Python](https://img.shields.io/badge/Python-3.11+-yellow)
![Package Manager](https://img.shields.io/badge/Package_Manager-UV-orange)
![License](https://img.shields.io/badge/License-MIT-red)

</div>

---

## 📋 Table of Contents

- [System Overview](#-system-overview)
- [Key Features](#-key-features)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [The Game: Odd/Even](#-the-game-oddeven)
- [Architecture](#-architecture)
- [Configuration](#-configuration)
- [Protocol Specification](#-protocol-specification)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [References](#-references)

---

## 🏆 System Overview

### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        LEAGUE LAYER                             │
│                     (League Manager)                            │
│   • Player Registration  • Scheduling  • Standings              │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       REFEREE LAYER                             │
│                     (Referee Agent)                             │
│   • Game Management  • Move Validation  • Result Declaration    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        GAME LAYER                               │
│                     (Odd/Even Game)                             │
│   • Move Legality  • Victory Conditions  • Game Logic           │
└─────────────────────────────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
    ┌──────────┐         ┌──────────┐         ┌──────────┐
    │ Player 1 │         │ Player 2 │         │ Player N │
    │   Agent  │         │   Agent  │         │   Agent  │
    └──────────┘         └──────────┘         └──────────┘
```

### 🔑 Core Design Principle: Separation of Concerns

> **IMPORTANT**: The League Layer and Referee Layer are **NOT dependent** on the specific game.
>
> You can replace the "Odd/Even" game with Tic-Tac-Toe, Chess, or any other game - **WITHOUT changing the general protocol**.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **MCP Protocol** | Full JSON-RPC 2.0 implementation with tools, resources, and prompts |
| **Multi-Agent System** | Autonomous AI agents competing against each other |
| **Round-Robin League** | Complete tournament management with standings |
| **LLM Integration** | Support for OpenAI and Anthropic for AI decision-making |
| **Scalable Architecture** | Designed for 100K+ players (modular & distributed) |
| **Error Resilience** | Exponential backoff, circuit breakers, retry logic |
| **UV Package Manager** | Lightning-fast dependency management |
| **Docker Ready** | Full containerization support for deployment |

---

## 📁 Project Structure

```
Assignment_7_MCP_Multi_Agent_Game/
├── src/
│   ├── client/                 # MCP Client Implementation
│   │   ├── mcp_client.py       # Main client
│   │   ├── session_manager.py  # Session management
│   │   ├── tool_registry.py    # Tool discovery & namespacing
│   │   ├── connection_manager.py # Health & retry logic
│   │   ├── message_queue.py    # Priority message handling
│   │   └── resource_manager.py # Resource & subscription management
│   │
│   ├── server/                 # MCP Server Implementation
│   │   ├── mcp_server.py       # Full MCP server
│   │   ├── base_server.py      # Game server base class
│   │   ├── tools/              # Tool implementations
│   │   └── resources/          # Resource definitions
│   │
│   ├── transport/              # Transport Layer
│   │   ├── json_rpc.py         # JSON-RPC 2.0 implementation
│   │   ├── http_transport.py   # HTTP communication
│   │   └── base.py             # Transport interface
│   │
│   ├── game/                   # Game Logic
│   │   ├── odd_even.py         # Odd/Even game implementation
│   │   └── match.py            # Match & scheduling
│   │
│   ├── agents/                 # AI Agents
│   │   ├── league_manager.py   # League management
│   │   ├── referee.py          # Game referee
│   │   └── player.py           # Player with strategies
│   │
│   ├── common/                 # Shared Utilities
│   │   ├── config.py           # Configuration management
│   │   ├── logger.py           # Structured logging
│   │   ├── exceptions.py       # Custom exceptions
│   │   └── protocol.py         # Protocol definitions
│   │
│   └── main.py                 # Main entry point
│
├── config/
│   └── servers.json            # Server configurations
│
├── tests/                      # Test Suite
│   ├── test_game.py
│   ├── test_transport.py
│   └── test_protocol.py
│
├── scripts/
│   ├── setup.sh                # Setup script (installs UV)
│   ├── run_league.sh           # Run league script
│   └── run_tests.sh            # Test runner
│
├── docs/
│   ├── ARCHITECTURE.md         # Detailed architecture diagrams
│   ├── API.md                  # API documentation
│   ├── DEPLOYMENT.md           # Deployment guide
│   └── DEVELOPMENT.md          # Development guide
│
├── pyproject.toml              # UV/Python project configuration
├── Makefile                    # Common commands
├── Dockerfile                  # Docker build
├── docker-compose.yml          # Multi-container orchestration
├── .python-version             # Python version for UV
├── .gitignore                  # Git ignore rules
├── REQUIREMENTS.md             # Full requirements specification
└── README.md                   # This file
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [UV](https://docs.astral.sh/uv/) package manager (recommended)
- Docker (optional, for containerized deployment)

### Installation with UV (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd Assignment_7_MCP_Multi_Agent_Game

# Option 1: One-command setup (installs UV if needed)
./scripts/setup.sh

# Option 2: Manual setup with UV
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync --all-extras

# Activate the environment
source .venv/bin/activate
```

### Alternative: Installation with pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev,llm]"
```

### Running the System

#### Option 1: Full League (Quick Start)

```bash
# Start everything with 4 players and run the league
uv run python -m src.main --run --players 4

# Or use Makefile
make run-league
```

#### Option 2: Individual Components

```bash
# Terminal 1: League Manager (port 8000)
uv run python -m src.main --component league

# Terminal 2: Referee (port 8001)
uv run python -m src.main --component referee

# Terminal 3: Player 1 (port 8101)
uv run python -m src.main --component player --name "AlphaBot" --port 8101 --register

# Terminal 4: Player 2 (port 8102)
uv run python -m src.main --component player --name "BetaBot" --port 8102 --register
```

#### Option 3: Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Or use Makefile
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

---

## 🎯 The Game: Odd/Even (זוגי/אי-זוגי)

A simple yet strategic game that allows focus on the architecture:

### Game Rules

| Step | Description |
|------|-------------|
| **1. Setup** | Each player is assigned a role (ODD or EVEN) |
| **2. Play** | Both players choose a number (1-5) simultaneously |
| **3. Resolution** | Sum is calculated |
| **4. Winner** | ODD sum → ODD player wins; EVEN sum → EVEN player wins |
| **5. Match** | Best of N rounds determines the match winner |

### Scoring System

| Result | Points |
|--------|--------|
| **Win** | 3 points |
| **Draw** | 1 point |
| **Loss** | 0 points |

---

## 🏗️ Architecture

### MCP Protocol Fundamentals

> **Model Context Protocol (MCP)** is a standard communication protocol for AI agents.
>
> Think of MCP like the **HTTP protocol** for the internet. Just as HTTP defines how browsers and servers communicate, **MCP defines how AI agents communicate**.

### Three MCP Primitives

| Primitive | Type | Description |
|-----------|------|-------------|
| **Resources** | Read-only | Data sources (standings, game state, history) |
| **Tools** | Active | Operations that perform actions and return results |
| **Prompts** | Templates | Predefined templates for agent interactions |

### Client Architecture Components

| Component | Responsibility |
|-----------|---------------|
| **Session Manager** | Track active sessions, manage concurrent connections |
| **Tool Registry** | Discover tools, handle namespace collisions (`server.tool`) |
| **Message Queue** | Priority-based FIFO queue with rate limiting |
| **Resource Manager** | Track resources, subscription mechanism, caching |
| **Connection Manager** | Heartbeat, retry logic, circuit breaker |
| **Transport Layer** | JSON serialization, HTTP/STDIO communication |

### Server Architecture

| Component | Port | Responsibilities |
|-----------|------|------------------|
| **League Manager** | 8000 | Player registration, scheduling, standings |
| **Referee** | 8001 | Game management, move validation, result declaration |
| **Players** | 81XX | Receive game state, make moves, report results |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture diagrams.

---

## 🔧 Configuration

### Port Configuration

| Component | Port | URL |
|-----------|------|-----|
| League Manager | 8000 | `http://localhost:8000/mcp` |
| Referee | 8001 | `http://localhost:8001/mcp` |
| Player 1 | 8101 | `http://localhost:8101/mcp` |
| Player 2 | 8102 | `http://localhost:8102/mcp` |
| Player N | 81XX | `http://localhost:81XX/mcp` |

### Environment Variables

```bash
# LLM Configuration (for AI strategies)
export OPENAI_API_KEY=your_key_here
export ANTHROPIC_API_KEY=your_key_here

# Logging
export LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Server Configuration
export LEAGUE_HOST=localhost
export LEAGUE_PORT=8000
export REFEREE_PORT=8001
```

### Server Configuration File

Edit `config/servers.json` to customize server settings:

```json
{
  "league_manager": {
    "host": "localhost",
    "port": 8000,
    "endpoint": "/mcp"
  },
  "referee": {
    "host": "localhost",
    "port": 8001,
    "endpoint": "/mcp"
  }
}
```

---

## 📨 Protocol Specification

### Protocol Version

All messages MUST include `"protocol": "league.v1"` - this is the version compatibility check.

### Basic Message Structure

```json
{
  "protocol": "league.v1",
  "message_type": "MOVE_REQUEST",
  "league_id": "league_2024_01",
  "round_id": 1,
  "match_id": "R1M1",
  "conversation_id": "uuid-here",
  "sender": "referee",
  "timestamp": "2024-12-13T10:00:00Z"
}
```

### Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `LEAGUE_REGISTER_REQUEST` | Player → League | Register to join league |
| `LEAGUE_REGISTER_RESPONSE` | League → Player | Registration confirmation |
| `GAME_START` | Referee → Players | Game begins |
| `MOVE_REQUEST` | Referee → Player | Request a move |
| `MOVE_RESPONSE` | Player → Referee | Submit move |
| `GAME_END` | Referee → Players | Game results |

### ⚠️ Critical Protocol Warning

> ⛔ **If your agent does not speak the protocol language EXACTLY as defined - it will be DISQUALIFIED.**
>
> - ❌ No half-compatibility
> - ❌ No "almost correct"
> - ✅ The protocol is a **BINDING CONTRACT**

---

## 🧪 Testing

### Running Tests

```bash
# Run all tests with UV
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_game.py -v

# Or use Makefile
make test
```

### Linting & Formatting

```bash
# Lint with Ruff
uv run ruff check src/ tests/

# Format code
uv run ruff format src/ tests/

# Type checking with MyPy
uv run mypy src/

# Or use Makefile
make lint
make format
make typecheck
```

---

## 🐳 Deployment

### Docker Deployment

```bash
# Build the image
docker build -t mcp-game-league .

# Run single container
docker run -p 8000:8000 -p 8001:8001 mcp-game-league

# Or use Docker Compose for full setup
docker-compose up --build -d
```

### Production Considerations

- Use environment variables for configuration
- Enable proper logging levels
- Configure resource limits in Docker
- Set up health checks for monitoring
- Use reverse proxy (nginx) for production traffic

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions.

---

## 📈 Grading Criteria

| Criterion | Description |
|-----------|-------------|
| **Architecture** | Modular, scalable design with clear separation |
| **Documentation** | PRD, architecture diagrams, code comments |
| **Git Usage** | Regular commits showing progress (not single commit!) |
| **Cost Analysis** | Token usage, compute costs estimation |
| **Terminology** | Consistent naming conventions throughout |
| **Error Handling** | Comprehensive error recovery mechanisms |
| **Testing** | Unit tests and integration tests |

---

## 🗺️ Roadmap

- [ ] WebSocket transport for real-time updates
- [ ] Web UI dashboard for league monitoring
- [ ] Additional game types (Tic-Tac-Toe, etc.)
- [ ] Kubernetes deployment manifests
- [ ] Advanced LLM strategies with fine-tuning
- [ ] Tournament brackets support
- [ ] Player statistics and analytics

---

## 📚 References

- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [UV Package Manager](https://docs.astral.sh/uv/)
- [Assignment Requirements](./REQUIREMENTS.md)
- [Architecture Documentation](./docs/ARCHITECTURE.md)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for development guidelines.

---

## 📄 License

MIT License - Academic project for LLMs and Multi-Agent Orchestration course.

---

<div align="center">

**Built with ❤️ for MIT-Level Excellence**

*Last Updated: December 2024*

</div>
