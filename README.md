# 🎮 MCP Multi-Agent Game League

> **Production-Grade Agentic AI System using Model Context Protocol (MCP)**
>
> A sophisticated multi-agent game system implementing autonomous AI agents that communicate via the Model Context Protocol (MCP) standard. Features intelligent players competing in a round-robin league tournament, with optional LLM-powered strategies using Anthropic Claude or OpenAI GPT.

<div align="center">

![Architecture](https://img.shields.io/badge/Architecture-3_Layer-blue)
![Protocol](https://img.shields.io/badge/Protocol-MCP_league.v2-green)
![Python](https://img.shields.io/badge/Python-3.11+-yellow)
![Package Manager](https://img.shields.io/badge/Package_Manager-UV-orange)
![License](https://img.shields.io/badge/License-MIT-red)
![Plugins](https://img.shields.io/badge/Plugins-Supported-purple)

</div>

---

## 📋 Table of Contents

- [System Overview](#-system-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [How to Operate](#-how-to-operate)
- [Plugins & Extensibility](#-plugins--extensibility)
- [Documentation](#-documentation)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [License](#-license)

---

## 🏆 System Overview

The **MCP Multi-Agent Game League** is a reference implementation of a distributed, autonomous multi-agent system. It demonstrates how independent AI agents can form a society (a league), govern themselves (Referees), and compete (Players) using strictly defined protocols.

### Key Features
*   **Autonomous Operation:** Zero-touch league management from registration to championship.
*   **Production-Grade Architecture:** Circuit breakers, exponential backoff, structured logging.
*   **Extensible Design:** Robust **Plugin System** and **Event Bus** for custom logic.
*   **LLM Integration:** Plug-and-play support for Anthropic Claude and OpenAI GPT strategies.
*   **Observability:** Comprehensive metrics and event hooks for system monitoring.

### High-Level System Architecture

```mermaid
graph TB
    subgraph "🏛️ League Layer"
        LM[League Manager<br/>Port 8000]
    end
    
    subgraph "⚖️ Referee Layer"
        REF1[Referee REF01<br/>Port 8001]
        REF2[Referee REF02<br/>Port 8002]
    end
    
    subgraph "🎲 Game Layer"
        GAME[Odd/Even Game Logic<br/>src/game/odd_even.py]
    end
    
    subgraph "🤖 Player Layer"
        P1[Player P01<br/>Port 8101<br/>random]
        P2[Player P02<br/>Port 8102<br/>pattern]
        P3[Player P03<br/>Port 8103<br/>llm]
        P4[Player P04<br/>Port 8104<br/>random]
    end
    
    LM <-->|"REFEREE_REGISTER<br/>MATCH_RESULT_REPORT"| REF1
    LM <-->|"REFEREE_REGISTER<br/>MATCH_RESULT_REPORT"| REF2
    
    REF1 <-->|"Game Logic<br/>Validation"| GAME
    REF2 <-->|"Game Logic<br/>Validation"| GAME
    
    REF1 <-->|"GAME_INVITE<br/>CHOOSE_PARITY_CALL<br/>GAME_OVER"| P1
    REF1 <-->|"GAME_INVITE<br/>CHOOSE_PARITY_CALL<br/>GAME_OVER"| P2
    REF2 <-->|"GAME_INVITE<br/>CHOOSE_PARITY_CALL<br/>GAME_OVER"| P3
    REF2 <-->|"GAME_INVITE<br/>CHOOSE_PARITY_CALL<br/>GAME_OVER"| P4
    
    P1 -.->|"LEAGUE_REGISTER_REQUEST"| LM
    P2 -.->|"LEAGUE_REGISTER_REQUEST"| LM
    P3 -.->|"LEAGUE_REGISTER_REQUEST"| LM
    P4 -.->|"LEAGUE_REGISTER_REQUEST"| LM
```

---

## 🏗️ Architecture

The system follows a strict **Three-Layer Architecture** to ensure separation of concerns and scalability.

1.  **League Layer:** Manages high-level tournament state (Standings, Schedules).
2.  **Referee Layer:** Manages individual match lifecycles and rule enforcement.
3.  **Game Layer:** Pure logic implementation of the game rules (Even/Odd).

See the [Full Architecture Documentation](docs/ARCHITECTURE.md) for detailed diagrams and state machines.

---

## 🚀 How to Operate

### Prerequisites

```bash
# Required
- Python 3.11+
- UV package manager (recommended) OR pip

# Optional (for LLM strategies)
export ANTHROPIC_API_KEY=your_key_here
export OPENAI_API_KEY=your_key_here
```

### Option 1: Full Automatic League (Recommended)

```bash
# Step 1: Install dependencies
uv sync --all-extras

# Step 2: Run the full league
uv run python -m src.main --run

# Step 3: Watch the tournament unfold!
```

### Option 2: Run with Plugins

The system automatically loads plugins from the `plugins/` directory.

```bash
# Run with system monitor plugin (metrics & logging)
uv run python -m src.main --run
```

---

## 🔌 Plugins & Extensibility

**New in v2.0:** The system now features a fully-fledged Plugin Architecture. You can extend the system without modifying core code.

### What can you do with plugins?
*   **Custom Strategies:** Add new player behaviors using `@strategy_plugin`.
*   **Observability:** Hook into `match.completed` or `agent.registered` events.
*   **Integrations:** Post results to Slack/Discord or save to a database.

See the [Plugin Development Guide](docs/PLUGINS.md) to get started.

---

## 📚 Documentation

We provide comprehensive documentation for every aspect of the system:

*   **[Product Requirements (PRD)](docs/PRD.md):** Detailed scope, functional requirements, and user stories.
*   **[Architecture Guide](docs/ARCHITECTURE.md):** Deep dive into system design, state machines, and message flows.
*   **[API Reference](docs/API.md):** Full specification of the JSON-RPC interface.
*   **[Protocol Specification](docs/protocol-spec.md):** Details on the custom `league.v2` protocol.
*   **[Plugin Guide](docs/PLUGINS.md):** How to create and register plugins.
*   **[Testing Flows](docs/TESTING_FLOWS.md):** Manual and automated testing procedures.

---

## 🧪 Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run plugin tests
uv run pytest tests/plugins/ -v
```

---

## 🐳 Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build
```

---

## 📄 License

MIT License

---

<div align="center">

**Built with ❤️ using Model Context Protocol**

*Last Updated: December 25, 2024*

</div>
