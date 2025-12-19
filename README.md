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

</div>

---

## 📋 Table of Contents

- [System Overview](#-system-overview)
- [Architecture](#-architecture)
- [How to Operate](#-how-to-operate)
- [Complete Game Flow](#-complete-game-flow)
- [Agent Communication](#-agent-communication)
- [State Machines](#-state-machines)
- [The Game: Odd/Even](#-the-game-oddeven)
- [Protocol Specification](#-protocol-specification)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)
- [Testing](#-testing)
- [Deployment](#-deployment)

---

## 🏆 System Overview

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

### 🔑 Key Design Principles

| Principle | Description | Implementation |
|-----------|-------------|----------------|
| **Separation of Concerns** | League/Referee layers are game-agnostic | Replace Odd/Even with any game without changing protocol |
| **Bidirectional MCP** | Each agent is BOTH server AND client | Enables peer-to-peer autonomous communication |
| **Round-Robin Assignment** | Referees assigned to matches in rotation | `MatchScheduler.create_round_robin_schedule()` |
| **Authentication Tokens** | Secure agent registration | `generate_auth_token()` in `protocol.py` |

---

## 🏗️ Architecture

### Three-Layer Architecture

```mermaid
graph TB
    subgraph "CONFIG LAYER"
        direction TB
        SYSTEM[config/system.json<br/>Protocol, Timeouts, Retry]
        AGENTS[config/agents/agents_config.json<br/>League Manager, Referees, Players]
        LEAGUE[config/leagues/league_2025_even_odd.json<br/>Scoring, Participants]
        GAMES[config/games/games_registry.json<br/>Game Types, Rules Modules]
        DEFAULTS[config/defaults/<br/>referee.json, player.json]
    end
    
    subgraph "DATA LAYER"
        direction TB
        STANDINGS[data/leagues/league_id/<br/>standings.json, rounds.json]
        MATCHES[data/matches/league_id/<br/>match_id.json]
        PLAYERS[data/players/player_id/<br/>history.json]
    end
    
    subgraph "LOG LAYER"
        direction TB
        LEAGUE_LOG[logs/league/league_id/<br/>*.log.jsonl]
        AGENT_LOG[logs/agents/<br/>*.log.jsonl]
        SYSTEM_LOG[logs/system/<br/>*.log.jsonl]
    end
    
    SYSTEM --> AGENTS
    AGENTS --> LEAGUE
    LEAGUE --> GAMES
    GAMES --> DEFAULTS
    
    STANDINGS --> MATCHES
    MATCHES --> PLAYERS
    
    LEAGUE_LOG --> AGENT_LOG
    AGENT_LOG --> SYSTEM_LOG
```

### MCP Server + Client Architecture (Each Agent)

```mermaid
graph TB
    subgraph "Each Agent = Server + Client"
        direction TB
        
        subgraph "Inbound - MCP Server"
            SERVER[📥 MCP Server<br/>Listens on port<br/>Exposes tools<br/>aiohttp + JSON-RPC 2.0]
        end
        
        subgraph "Outbound - MCP Client"  
            CLIENT[📤 MCP Client<br/>httpx AsyncClient<br/>Calls other agents' tools]
        end
        
        subgraph "Business Logic"
            LOGIC[Agent Logic<br/>State Management<br/>Strategy Execution]
        end
    end
    
    LOGIC --> SERVER
    LOGIC --> CLIENT
    
    OTHERS1[Other Agents] -->|"HTTP POST /mcp<br/>tools/call"| SERVER
    CLIENT -->|"HTTP POST /mcp<br/>tools/call"| OTHERS2[Other Agents]
```

### Component Interaction Map

```mermaid
flowchart LR
    subgraph External["Entry Points"]
        CLI[🖥️ src/main.py<br/>CLI + Orchestrator]
        CFG[⚙️ src/common/config.py<br/>Configuration]
    end
    
    subgraph Agents["Agent Layer"]
        LM[league_manager.py<br/>Registration, Scheduling]
        REF[referee.py<br/>Match Management]
        PLAYER[player.py<br/>Strategies]
    end
    
    subgraph Core["Core Components"]
        PROTO[protocol.py<br/>20+ Message Types]
        MATCH[match.py<br/>MatchScheduler]
        GAME[odd_even.py<br/>Game Rules]
    end
    
    subgraph Infra["Infrastructure"]
        BASE[base_server.py<br/>MCP Server Base]
        MCP[mcp_client.py<br/>HTTP Client]
        TRANSPORT[http_transport.py<br/>JSON-RPC Handler]
    end
    
    CLI --> LM
    CLI --> REF
    CLI --> PLAYER
    CFG --> CLI
    
    LM --> MATCH
    LM --> PROTO
    LM --> BASE
    
    REF --> GAME
    REF --> PROTO
    REF --> BASE
    REF --> MCP
    
    PLAYER --> PROTO
    PLAYER --> BASE
    PLAYER --> MCP
    
    BASE --> TRANSPORT
    MCP --> TRANSPORT
```

---

## 🚀 How to Operate

### Quick Start Flowchart

```mermaid
flowchart TD
    START([🚀 Start]) --> CHECK{Dependencies<br/>Installed?}
    
    CHECK -->|No| SETUP[Run Setup]
    SETUP --> UV_INSTALL["uv sync --all-extras"]
    UV_INSTALL --> CHECK
    
    CHECK -->|Yes| MODE{Run Mode?}
    
    MODE -->|"🎯 Automatic<br/>(Recommended)"| AUTO["uv run python -m src.main --run"]
    MODE -->|"🔧 Manual<br/>(Multi-terminal)"| MANUAL[Start Components<br/>Separately]
    MODE -->|"🐳 Docker"| DOCKER["docker-compose up --build"]
    
    AUTO --> AUTO_FLOW[System automatically:<br/>1. Starts League Manager :8000<br/>2. Starts 2 Referees :8001-8002<br/>3. Starts 4 Players :8101-8104<br/>4. Registers all agents<br/>5. Runs round-robin tournament<br/>6. Displays final standings]
    
    MANUAL --> T1["Terminal 1:<br/>uv run python -m src.main<br/>--component league"]
    T1 --> T2["Terminal 2:<br/>uv run python -m src.main<br/>--component referee --register"]
    T2 --> T3["Terminal 3-6:<br/>uv run python -m src.main<br/>--component player --name P01<br/>--port 8101 --register"]
    T3 --> T7["Terminal 7:<br/>uv run python -m src.main<br/>--start-league<br/>--run-all-rounds"]
    
    AUTO_FLOW --> COMPLETE([🏆 League Complete])
    T7 --> COMPLETE
    DOCKER --> COMPLETE
```

### Step-by-Step Instructions

#### Prerequisites

```bash
# Required
- Python 3.11+
- UV package manager (recommended) OR pip

# Optional (for LLM strategies)
export ANTHROPIC_API_KEY=your_key_here
export OPENAI_API_KEY=your_key_here
```

#### Option 1: Full Automatic League (Recommended)

```bash
# Step 1: Install dependencies
uv sync --all-extras
# OR with pip:
pip install -e '.[dev,llm]'

# Step 2: Run the full league (defaults: 1 League Manager, 2 Referees, 4 Players)
uv run python -m src.main --run

# Step 3: Watch the output - system automatically:
#   - Starts League Manager (port 8000)
#   - Starts 2 Referees (ports 8001, 8002)
#   - Starts 4 Players (ports 8101-8104)
#   - Registers all agents
#   - Runs round-robin tournament (6 matches for 4 players)
#   - Displays standings after each round
#   - Declares champion
```

#### Option 2: Custom Configuration

```bash
# Run with 6 players and 3 referees
uv run python -m src.main --run --players 6 --referees 3

# Run with LLM strategies (Claude)
uv run python -m src.main --run --strategy llm

# Run with mixed strategies
uv run python -m src.main --run --strategy mixed

# Run with debug logging
uv run python -m src.main --run --debug
```

#### Option 3: Manual Multi-Terminal Setup

```bash
# Terminal 1: Start League Manager
uv run python -m src.main --component league --debug

# Terminal 2: Start Referee 1
uv run python -m src.main --component referee --port 8001 --register

# Terminal 3: Start Referee 2 (optional)
uv run python -m src.main --component referee --port 8002 --register

# Terminal 4-7: Start Players
uv run python -m src.main --component player --name "AlphaBot" --port 8101 --register
uv run python -m src.main --component player --name "BetaBot" --port 8102 --register --strategy pattern
uv run python -m src.main --component player --name "ClaudeBot" --port 8103 --register --strategy llm
uv run python -m src.main --component player --name "DeltaBot" --port 8104 --register

# Terminal 8: Control Commands
uv run python -m src.main --start-league       # Create schedule
uv run python -m src.main --run-round          # Run one round
uv run python -m src.main --run-all-rounds     # Run all remaining rounds
uv run python -m src.main --get-standings      # Get current standings
```

#### Option 4: Docker

```bash
# Build and run
docker-compose up --build

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Command Reference Table

| Command | Description |
|---------|-------------|
| `--run` | Run full automatic league |
| `--players N` | Number of players (default: 4) |
| `--referees N` | Number of referees (default: 2) |
| `--strategy [random\|pattern\|llm\|mixed]` | Player strategy type |
| `--component [league\|referee\|player]` | Start single component |
| `--name NAME` | Player display name |
| `--port PORT` | Component port |
| `--register` | Auto-register with league |
| `--start-league` | Send start_league command |
| `--run-round` | Run next round |
| `--run-all-rounds` | Run all remaining rounds |
| `--get-standings` | Get current standings |
| `--debug` | Enable debug logging |
| `--llm-provider [anthropic\|openai]` | LLM provider |
| `--llm-model MODEL` | LLM model name |

### Makefile Commands

```bash
make setup        # Install UV and dependencies
make run-league   # Run full league
make run-debug    # Run with debug logging
make test         # Run all tests
make lint         # Check code quality
make docker-up    # Start with Docker
make docker-down  # Stop Docker services
```

---

## 🔄 Complete Game Flow

### Full League Operation Sequence

```mermaid
sequenceDiagram
    autonumber
    participant ORCH as 🎯 Orchestrator<br/>main.py
    participant LM as 🏛️ League Manager<br/>:8000
    participant REF1 as ⚖️ Referee 1<br/>:8001
    participant REF2 as ⚖️ Referee 2<br/>:8002
    participant P1 as 🤖 P01<br/>:8101
    participant P2 as 🤖 P02<br/>:8102
    participant P3 as 🤖 P03<br/>:8103
    participant P4 as 🤖 P04<br/>:8104
    
    Note over ORCH,P4: Phase 1: System Startup
    
    ORCH->>LM: start()
    LM-->>ORCH: Running on :8000
    
    par Start Referees
        ORCH->>REF1: start()
        REF1-->>ORCH: Running on :8001
        and
        ORCH->>REF2: start()
        REF2-->>ORCH: Running on :8002
    end
    
    par Start Players
        ORCH->>P1: start()
        and
        ORCH->>P2: start()
        and
        ORCH->>P3: start()
        and
        ORCH->>P4: start()
    end
    
    Note over ORCH,P4: Phase 2: Registration
    
    par Referee Registration
        REF1->>LM: REFEREE_REGISTER_REQUEST
        LM-->>REF1: REFEREE_REGISTER_RESPONSE ✓ auth_token
        and
        REF2->>LM: REFEREE_REGISTER_REQUEST
        LM-->>REF2: REFEREE_REGISTER_RESPONSE ✓ auth_token
    end
    
    par Player Registration
        P1->>LM: LEAGUE_REGISTER_REQUEST
        LM-->>P1: LEAGUE_REGISTER_RESPONSE ✓ auth_token
        and
        P2->>LM: LEAGUE_REGISTER_REQUEST
        LM-->>P2: LEAGUE_REGISTER_RESPONSE ✓ auth_token
        and
        P3->>LM: LEAGUE_REGISTER_REQUEST
        LM-->>P3: LEAGUE_REGISTER_RESPONSE ✓ auth_token
        and
        P4->>LM: LEAGUE_REGISTER_REQUEST
        LM-->>P4: LEAGUE_REGISTER_RESPONSE ✓ auth_token
    end
    
    Note over ORCH,P4: Phase 3: Schedule Creation
    
    LM->>LM: create_round_robin_schedule()
    Note over LM: 4 players = 6 matches<br/>Round 1: P1vP2, P3vP4<br/>Round 2: P1vP3, P2vP4<br/>Round 3: P1vP4, P2vP3
    
    Note over ORCH,P4: Phase 4: Round Execution
    
    loop Each Round
        LM->>LM: ROUND_ANNOUNCEMENT
        LM->>REF1: assign_match(P1 vs P2)
        LM->>REF2: assign_match(P3 vs P4)
        
        Note over REF1,P2: Match 1: P1 vs P2
        REF1->>P1: GAME_INVITE {role: ODD}
        REF1->>P2: GAME_INVITE {role: EVEN}
        P1-->>REF1: GAME_JOIN_ACK
        P2-->>REF1: GAME_JOIN_ACK
        
        loop Best of N rounds
            REF1->>P1: CHOOSE_PARITY_CALL {deadline}
            REF1->>P2: CHOOSE_PARITY_CALL {deadline}
            P1-->>REF1: CHOOSE_PARITY_RESPONSE {number: 3}
            P2-->>REF1: CHOOSE_PARITY_RESPONSE {number: 2}
            REF1->>REF1: sum=5 (ODD) → P1 wins round
            REF1->>P1: ROUND_RESULT
            REF1->>P2: ROUND_RESULT
        end
        
        REF1->>P1: GAME_OVER {winner, score}
        REF1->>P2: GAME_OVER {winner, score}
        REF1->>LM: MATCH_RESULT_REPORT
        
        Note over REF2,P4: Match 2: P3 vs P4 (parallel)
        
        LM->>LM: Update standings
        LM->>LM: LEAGUE_STANDINGS_UPDATE
    end
    
    Note over ORCH,P4: Phase 5: League Complete
    
    LM->>LM: Determine champion
    LM-->>ORCH: LEAGUE_COMPLETED {champion, final_standings}
```

### Single Match Flow (Detailed)

```mermaid
sequenceDiagram
    autonumber
    participant REF as ⚖️ Referee
    participant P1 as 🤖 Player 1<br/>(ODD)
    participant P2 as 🤖 Player 2<br/>(EVEN)
    participant GAME as 🎲 Game Logic
    
    Note over REF,GAME: Match Setup
    
    REF->>P1: GAME_INVITE
    Note right of REF: {match_id, opponent_id,<br/>assigned_role: "ODD",<br/>game_type: "even_odd",<br/>best_of: 5}
    
    REF->>P2: GAME_INVITE
    Note right of REF: {match_id, opponent_id,<br/>assigned_role: "EVEN",<br/>game_type: "even_odd",<br/>best_of: 5}
    
    P1-->>REF: GAME_JOIN_ACK {accepted: true}
    P2-->>REF: GAME_JOIN_ACK {accepted: true}
    
    Note over REF,GAME: Game Rounds (Best of 5)
    
    loop Round 1 to N (until winner)
        REF->>P1: CHOOSE_PARITY_CALL
        Note right of REF: {game_round: 1,<br/>current_score: {ODD: 0, EVEN: 0},<br/>deadline: "2024-12-19T12:00:30Z"}
        
        REF->>P2: CHOOSE_PARITY_CALL
        
        P1->>P1: Strategy.choose_move()
        P2->>P2: Strategy.choose_move()
        
        P1-->>REF: CHOOSE_PARITY_RESPONSE {number: 3}
        P2-->>REF: CHOOSE_PARITY_RESPONSE {number: 2}
        
        REF->>GAME: validate(3, 2)
        GAME-->>REF: valid
        
        REF->>GAME: calculate_result(3, 2)
        Note over GAME: sum = 5 (ODD)<br/>ODD player wins
        GAME-->>REF: {winner: "ODD", sum: 5}
        
        REF->>P1: ROUND_RESULT
        Note right of REF: {round_winner: "ODD",<br/>you_won: true,<br/>your_number: 3,<br/>opponent_number: 2,<br/>sum: 5,<br/>updated_score: {ODD: 1, EVEN: 0}}
        
        REF->>P2: ROUND_RESULT
        Note right of REF: {round_winner: "ODD",<br/>you_won: false, ...}
    end
    
    Note over REF,GAME: Match Complete
    
    REF->>P1: GAME_OVER
    Note right of REF: {match_winner: "P1",<br/>final_score: {ODD: 3, EVEN: 1},<br/>rounds_played: 4}
    
    REF->>P2: GAME_OVER
```

---

## 💬 Agent Communication

### Message Flow Overview

```mermaid
flowchart TB
    subgraph "Registration Phase"
        REF_REG[REFEREE_REGISTER_REQUEST] --> REF_RES[REFEREE_REGISTER_RESPONSE]
        PLAYER_REG[LEAGUE_REGISTER_REQUEST] --> PLAYER_RES[LEAGUE_REGISTER_RESPONSE]
    end
    
    subgraph "Match Setup Phase"
        ROUND_ANN[ROUND_ANNOUNCEMENT] --> GAME_INV[GAME_INVITE]
        GAME_INV --> GAME_ACK[GAME_JOIN_ACK]
    end
    
    subgraph "Game Play Phase"
        PARITY_CALL[CHOOSE_PARITY_CALL] --> PARITY_RES[CHOOSE_PARITY_RESPONSE]
        PARITY_RES --> ROUND_RES[ROUND_RESULT]
        ROUND_RES -->|"More rounds"| PARITY_CALL
    end
    
    subgraph "Completion Phase"
        GAME_END[GAME_OVER] --> MATCH_REPORT[MATCH_RESULT_REPORT]
        MATCH_REPORT --> STANDINGS[LEAGUE_STANDINGS_UPDATE]
        STANDINGS -->|"More matches"| ROUND_ANN
        STANDINGS -->|"League done"| COMPLETE[LEAGUE_COMPLETED]
    end
    
    REF_RES --> ROUND_ANN
    PLAYER_RES --> ROUND_ANN
    GAME_ACK --> PARITY_CALL
    ROUND_RES -->|"Match complete"| GAME_END
```

### Protocol Message Types (20+)

```mermaid
classDiagram
    class BaseMessage {
        +string protocol = "league.v2"
        +string message_type
        +string league_id
        +string conversation_id
        +string sender
        +datetime timestamp
    }
    
    class LEAGUE_REGISTER_REQUEST {
        +string player_id
        +string display_name
        +string endpoint
        +string[] game_types
    }
    
    class LEAGUE_REGISTER_RESPONSE {
        +bool success
        +string auth_token
        +dict league_info
        +string error
    }
    
    class REFEREE_REGISTER_REQUEST {
        +string referee_id
        +string endpoint
        +string[] supported_games
    }
    
    class GAME_INVITE {
        +string match_id
        +string opponent_id
        +string assigned_role
        +string game_type
        +int best_of
    }
    
    class CHOOSE_PARITY_CALL {
        +int game_round
        +dict current_score
        +datetime deadline
    }
    
    class CHOOSE_PARITY_RESPONSE {
        +int number
        +dict metadata
    }
    
    class GAME_OVER {
        +string match_winner
        +dict final_score
        +int rounds_played
    }
    
    class MATCH_RESULT_REPORT {
        +string match_id
        +string winner_id
        +dict score
        +list round_details
    }
    
    BaseMessage <|-- LEAGUE_REGISTER_REQUEST
    BaseMessage <|-- LEAGUE_REGISTER_RESPONSE
    BaseMessage <|-- REFEREE_REGISTER_REQUEST
    BaseMessage <|-- GAME_INVITE
    BaseMessage <|-- CHOOSE_PARITY_CALL
    BaseMessage <|-- CHOOSE_PARITY_RESPONSE
    BaseMessage <|-- GAME_OVER
    BaseMessage <|-- MATCH_RESULT_REPORT
```

### Message Timeouts

| Message Type | Timeout |
|--------------|---------|
| `REFEREE_REGISTER` | 10 seconds |
| `GAME_JOIN_ACK` | 10 seconds |
| `CHOOSE_PARITY` (Move) | 30 seconds |
| `MATCH_RESULT_REPORT` | 10 seconds |
| `LEAGUE_QUERY` | 10 seconds |
| Generic Response | 10 seconds |

---

## 🔀 State Machines

### Player Agent States

```mermaid
stateDiagram-v2
    [*] --> INIT: Create Player
    
    INIT --> REGISTERED: LEAGUE_REGISTER_RESPONSE ✓
    INIT --> INIT: Registration failed (retry)
    
    REGISTERED --> ACTIVE: GAME_INVITE received
    REGISTERED --> SUSPENDED: Timeout / Error
    
    ACTIVE --> IN_GAME: GAME_JOIN_ACK sent
    
    IN_GAME --> ACTIVE: GAME_OVER received
    IN_GAME --> SUSPENDED: Disconnected
    
    ACTIVE --> REGISTERED: Match complete
    
    SUSPENDED --> REGISTERED: Reconnected
    SUSPENDED --> SHUTDOWN: Max retries exceeded
    
    REGISTERED --> SHUTDOWN: LEAGUE_COMPLETED
    ACTIVE --> SHUTDOWN: LEAGUE_COMPLETED
    
    SHUTDOWN --> [*]
    
    note right of INIT: Initial state
    note right of REGISTERED: Ready to receive invites
    note right of ACTIVE: Processing game invitation
    note right of IN_GAME: Playing match
    note right of SUSPENDED: Temporarily unavailable
```

### Referee Agent States

```mermaid
stateDiagram-v2
    [*] --> INIT: Create Referee
    
    INIT --> READY: REFEREE_REGISTER_RESPONSE ✓
    
    READY --> MANAGING_MATCH: Match assigned
    
    MANAGING_MATCH --> WAITING_ACCEPTS: GAME_INVITE sent
    
    WAITING_ACCEPTS --> GAME_RUNNING: All GAME_JOIN_ACK received
    WAITING_ACCEPTS --> READY: Timeout (forfeit)
    
    GAME_RUNNING --> WAITING_MOVES: CHOOSE_PARITY_CALL sent
    
    WAITING_MOVES --> RESOLVING_ROUND: Both moves received
    WAITING_MOVES --> GAME_RUNNING: Timeout (default move)
    
    RESOLVING_ROUND --> GAME_RUNNING: More rounds needed
    RESOLVING_ROUND --> REPORTING_RESULT: Match complete
    
    REPORTING_RESULT --> READY: MATCH_RESULT_REPORT acknowledged
    
    READY --> SHUTDOWN: League ended
    
    SHUTDOWN --> [*]
```

### League Manager States

```mermaid
stateDiagram-v2
    [*] --> INIT: Create League
    
    INIT --> REGISTRATION_OPEN: Start registration
    
    REGISTRATION_OPEN --> READY: Min players reached
    REGISTRATION_OPEN --> REGISTRATION_OPEN: Agent registered
    
    READY --> RUNNING: start_league() called
    
    RUNNING --> ROUND_IN_PROGRESS: start_next_round()
    
    ROUND_IN_PROGRESS --> BETWEEN_ROUNDS: All matches complete
    
    BETWEEN_ROUNDS --> ROUND_IN_PROGRESS: More rounds
    BETWEEN_ROUNDS --> COMPLETE: All rounds done
    
    COMPLETE --> SHUTDOWN: Cleanup
    
    SHUTDOWN --> [*]
    
    note right of REGISTRATION_OPEN: Accepting registrations
    note right of READY: Enough players, schedule ready
    note right of RUNNING: Tournament active
    note right of COMPLETE: Champion determined
```

---

## 🎯 The Game: Odd/Even

### Game Rules

```mermaid
flowchart TD
    START([🎮 Match Start]) --> ASSIGN[Assign Roles Randomly]
    
    ASSIGN --> P1_ODD[Player 1: ODD]
    ASSIGN --> P2_EVEN[Player 2: EVEN]
    
    P1_ODD --> ROUND[🔄 Round N]
    P2_EVEN --> ROUND
    
    ROUND --> CHOOSE[Both players choose<br/>number 1-5 secretly]
    
    CHOOSE --> SUM[Calculate sum]
    
    SUM --> CHECK{Sum % 2 == 0?}
    
    CHECK -->|"Yes (EVEN)"| EVEN_WIN[🎯 EVEN player wins round]
    CHECK -->|"No (ODD)"| ODD_WIN[🎯 ODD player wins round]
    
    EVEN_WIN --> UPDATE[Update score]
    ODD_WIN --> UPDATE
    
    UPDATE --> WINNER_CHECK{Best of N<br/>winner?}
    
    WINNER_CHECK -->|No| ROUND
    WINNER_CHECK -->|Yes| MATCH_END[Determine match winner]
    
    MATCH_END --> END([🏆 Match Complete])
```

### Scoring System

| Match Result | League Points |
|--------------|---------------|
| **Win** | 3 points |
| **Draw** | 1 point |
| **Loss** | 0 points |

### Player Strategies

```mermaid
graph TB
    subgraph "Strategy Types"
        RANDOM[🎲 RandomStrategy<br/>Uniform random 1-5]
        PATTERN[📊 PatternStrategy<br/>Exploits opponent patterns]
        LLM[🧠 LLMStrategy<br/>AI-powered decisions]
    end
    
    subgraph "LLM Providers"
        ANTHROPIC[🟣 Anthropic Claude<br/>claude-3-5-sonnet]
        OPENAI[🟢 OpenAI GPT<br/>gpt-4o-mini]
        FALLBACK[🔄 Fallback<br/>Random on error]
    end
    
    LLM -->|Primary| ANTHROPIC
    LLM -->|Alternative| OPENAI
    LLM -->|On Error| FALLBACK
```

---

## 📨 Protocol Specification

### JSON-RPC 2.0 Format

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "tools/call",
  "params": {
    "name": "receive_game_invite",
    "arguments": {
      "protocol": "league.v2",
      "message_type": "GAME_INVITE",
      "league_id": "league_2025_even_odd",
      "match_id": "match_001",
      "opponent_id": "P02",
      "assigned_role": "ODD",
      "game_type": "even_odd",
      "best_of": 5
    }
  }
}
```

### Message Examples

See `docs/message-examples/` for all 18+ example messages:

- `registration/referee_register_request.json`
- `registration/player_register_request.json`
- `game_invite.json`
- `choose_parity.json`
- `game_over.json`
- `match_result_report.json`
- `standings_update.json`
- And more...

---

## 🔧 Configuration

### Port Configuration

| Component | Default Port | URL |
|-----------|--------------|-----|
| League Manager | 8000 | `http://localhost:8000/mcp` |
| Referee 1 | 8001 | `http://localhost:8001/mcp` |
| Referee 2 | 8002 | `http://localhost:8002/mcp` |
| Player 1 (P01) | 8101 | `http://localhost:8101/mcp` |
| Player 2 (P02) | 8102 | `http://localhost:8102/mcp` |
| Player 3 (P03) | 8103 | `http://localhost:8103/mcp` |
| Player 4 (P04) | 8104 | `http://localhost:8104/mcp` |
| Player N | 81XX | `http://localhost:81XX/mcp` |

### Configuration Files

| File | Purpose |
|------|---------|
| `config/system.json` | Global system settings, timeouts, retry policy |
| `config/agents/agents_config.json` | Agent definitions (LM, Referees, Players) |
| `config/leagues/league_2025_even_odd.json` | League scoring and participant limits |
| `config/games/games_registry.json` | Game type definitions and rules modules |
| `config/defaults/referee.json` | Default referee settings |
| `config/defaults/player.json` | Default player settings |

### Environment Variables

```bash
# LLM Configuration
export ANTHROPIC_API_KEY=your_anthropic_key
export OPENAI_API_KEY=your_openai_key

# Logging
export LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Server Configuration (optional overrides)
export LEAGUE_HOST=localhost
export LEAGUE_PORT=8000
```

---

## 📁 Project Structure

```
MCP_Multi_Agent_Game/
├── src/                           # Source code
│   ├── main.py                    # 🎯 Main entry point & orchestrator
│   ├── agents/                    # Agent implementations
│   │   ├── league_manager.py      # 🏛️ League Manager agent
│   │   ├── referee.py             # ⚖️ Referee agent  
│   │   └── player.py              # 🤖 Player agent + strategies
│   ├── game/                      # Game logic
│   │   ├── odd_even.py            # 🎲 Odd/Even game rules
│   │   ├── match.py               # 📅 Match scheduling
│   │   └── registry.py            # Game type registry
│   ├── common/                    # Shared utilities (≈ league_sdk)
│   │   ├── config.py              # Configuration management
│   │   ├── config_loader.py       # Config file loader
│   │   ├── protocol.py            # 📨 Message types & factories
│   │   ├── repositories.py        # Data persistence
│   │   ├── logger.py              # Structured logging
│   │   ├── lifecycle.py           # Agent lifecycle management
│   │   └── exceptions.py          # Custom exceptions
│   ├── server/                    # MCP Server implementation
│   │   ├── base_server.py         # Base MCP server class
│   │   ├── mcp_server.py          # Full MCP server
│   │   ├── tools/                 # Tool implementations
│   │   └── resources/             # Resource definitions
│   ├── client/                    # MCP Client implementation
│   │   ├── mcp_client.py          # HTTP client
│   │   ├── session_manager.py     # Session management
│   │   ├── connection_manager.py  # Connection & retry
│   │   ├── message_queue.py       # Message queuing
│   │   ├── tool_registry.py       # Tool discovery
│   │   └── resource_manager.py    # Resource management
│   └── transport/                 # Transport layer
│       ├── json_rpc.py            # JSON-RPC 2.0
│       ├── http_transport.py      # HTTP communication
│       └── base.py                # Transport interface
│
├── config/                        # Configuration layer
│   ├── system.json                # System-wide config
│   ├── agents/agents_config.json  # Agent definitions
│   ├── leagues/league_2025_even_odd.json
│   ├── games/games_registry.json
│   ├── defaults/                  # Default settings
│   └── servers.json               # Server registry
│
├── data/                          # Runtime data layer
│   ├── leagues/league_2025_even_odd/
│   │   ├── standings.json         # Current standings
│   │   └── rounds.json            # Round history
│   ├── matches/league_2025_even_odd/
│   └── players/                   # Player history
│       ├── P01/history.json
│       └── P02/history.json
│
├── logs/                          # Logging layer
│   ├── league/league_2025_even_odd/
│   ├── agents/
│   └── system/
│
├── docs/                          # Documentation
│   ├── protocol-spec.md           # Protocol specification
│   ├── message-examples/          # 18+ JSON examples
│   ├── ARCHITECTURE.md
│   ├── COMMAND_REFERENCE.md
│   ├── DEPLOYMENT.md
│   └── DEVELOPMENT.md
│
├── tests/                         # Test suite
│   ├── test_game.py
│   ├── test_protocol.py
│   ├── test_transport.py
│   └── ...
│
├── scripts/                       # Utility scripts
│   ├── setup.sh
│   ├── run_league.sh
│   └── run_tests.sh
│
├── pyproject.toml                 # Project configuration
├── Makefile                       # Common commands
├── Dockerfile                     # Docker build
├── docker-compose.yml             # Multi-container setup
├── README.md                      # This file
└── REQUIREMENTS.md                # Requirements specification
```

---

## 🧪 Testing

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Run specific test
uv run pytest tests/test_game.py -v
uv run pytest tests/test_protocol.py -v
uv run pytest tests/test_transport.py -v

# Or use Makefile
make test
```

---

## 🐳 Deployment

### Docker Deployment

```bash
# Build and run all services
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f league_manager
docker-compose logs -f referee
docker-compose logs -f player1

# Stop all services
docker-compose down
```

### Production Considerations

- Set `LOG_LEVEL=INFO` in production
- Configure proper timeouts in `config/system.json`
- Use environment variables for secrets (API keys)
- Enable retry policy with exponential backoff

---

## 📚 References

- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [UV Package Manager](https://docs.astral.sh/uv/)
- [Project Requirements](./REQUIREMENTS.md)
- [Protocol Specification](./docs/protocol-spec.md)
- [Architecture Documentation](./docs/ARCHITECTURE.md)
- [Command Reference](./docs/COMMAND_REFERENCE.md)

---

## 📄 License

MIT License

---

<div align="center">

**Built with ❤️ using Model Context Protocol**

*Last Updated: December 2024*

</div>
