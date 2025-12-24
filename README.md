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
    LM --> MCP
    
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

**Note**: All agents (League Manager, Referee, Player) use both MCP Server (inbound) and MCP Client (outbound) for bidirectional communication.

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

#### Option 2.5: With Real-Time Interactive Dashboard 🎨 (Innovation #4)

```bash
# Run tournament with live dashboard visualization
uv run python -m src.main --run --players 4 --dashboard

# Then open your browser to:
# http://localhost:8050

# What you'll see:
# ✓ Real-time tournament overview with live standings
# ✓ Strategy performance charts (win rates over time)
# ✓ Live game event stream
# ✓ Interactive Plotly visualizations (zoom, pan, export)
# ✓ Data export functionality

# Advanced: Run with LLM strategies AND dashboard
export ANTHROPIC_API_KEY=your-key
uv run python -m src.main --run --players 4 --strategy llm --dashboard

# Using the demo script:
python examples/dashboard/run_with_dashboard.py --players 6 --rounds 20
```

**Dashboard Features:**
- 📊 **Real-Time Visualization**: Watch tournaments unfold live via WebSocket streaming
- 🎯 **Strategy Performance**: Compare win rates and scores across different strategies
- 📈 **Interactive Charts**: Plotly-powered charts with zoom, pan, and export
- 🏆 **Live Standings**: Updated after each match with rankings and statistics
- 📝 **Event Log**: Complete timestamped history of all game actions
- 💾 **Data Export**: Download all data as JSON for further analysis

See [examples/dashboard/README.md](examples/dashboard/README.md) and [docs/DASHBOARD.md](docs/DASHBOARD.md) for complete documentation.

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
    Note over LM: 4 players = 6 matches<br/>Round 1: P01vP04, P02vP03<br/>Round 2: P01vP03, P04vP02<br/>Round 3: P01vP02, P03vP04
    
    Note over ORCH,P4: Phase 4: Round Execution (showing Round 1)
    
    LM->>LM: ROUND_ANNOUNCEMENT
    LM->>REF1: start_match(P01 vs P04)
    LM->>REF2: start_match(P02 vs P03)
    
    Note over REF1,P4: Match R1M1: P01 vs P04
    REF1->>P1: GAME_INVITE {role: ODD}
    REF1->>P4: GAME_INVITE {role: EVEN}
    P1-->>REF1: GAME_JOIN_ACK
    P4-->>REF1: GAME_JOIN_ACK
    
    loop Best of 5 rounds
        REF1->>P1: CHOOSE_PARITY_CALL {deadline}
        REF1->>P4: CHOOSE_PARITY_CALL {deadline}
        P1-->>REF1: CHOOSE_PARITY_RESPONSE {number: 3}
        P4-->>REF1: CHOOSE_PARITY_RESPONSE {number: 2}
        REF1->>REF1: sum=5 (ODD) → P01 wins round
        REF1->>P1: ROUND_RESULT
        REF1->>P4: ROUND_RESULT
    end
    
    REF1->>P1: GAME_OVER {winner: P01}
    REF1->>P4: GAME_OVER {winner: P01}
    REF1->>LM: MATCH_RESULT_REPORT
    
    Note over REF2,P3: Match R1M2: P02 vs P03 (parallel)
    
    LM->>LM: Update standings
    LM->>LM: LEAGUE_STANDINGS_UPDATE
    
    Note over ORCH,P4: Rounds 2 and 3 follow same pattern
    
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
    Note right of REF: {game_id, match_id,<br/>opponent_id,<br/>assigned_role: "ODD",<br/>rounds_to_play: 5}
    
    REF->>P2: GAME_INVITE
    Note right of REF: {game_id, match_id,<br/>opponent_id,<br/>assigned_role: "EVEN",<br/>rounds_to_play: 5}
    
    P1-->>REF: GAME_JOIN_ACK {accepted: true}
    P2-->>REF: GAME_JOIN_ACK {accepted: true}
    
    Note over REF,GAME: Game Rounds (Best of 5)
    
    loop Round 1 to N (until winner)
        REF->>P1: CHOOSE_PARITY_CALL
        Note right of REF: {match_id, player_id,<br/>round_id: 1,<br/>your_standings: {wins: 0, losses: 0},<br/>deadline: "2024-12-23T12:00:30Z"}
        
        REF->>P2: CHOOSE_PARITY_CALL
        
        P1->>P1: Strategy.choose_move()
        P2->>P2: Strategy.choose_move()
        
        P1-->>REF: CHOOSE_PARITY_RESPONSE {parity_choice: 3}
        P2-->>REF: CHOOSE_PARITY_RESPONSE {parity_choice: 2}
        
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
    Note right of REF: {match_id, status: "WIN",<br/>winner_player_id: "P01",<br/>drawn_number, number_parity,<br/>choices}
    
    REF->>P2: GAME_OVER
```

**Code Reference**: `src/agents/referee.py` → `RefereeAgent._run_game_round()`

### Single Round Communication Flow

```mermaid
flowchart TD
    START([Round Start]) --> REQ_MOVES
    
    subgraph "Move Collection Phase"
        REQ_MOVES[📤 Referee sends<br/>CHOOSE_PARITY_CALL<br/>to both players]
        
        REQ_MOVES --> P1_DECIDE
        REQ_MOVES --> P2_DECIDE
        
        P1_DECIDE[🤖 Player 1<br/>Strategy.decide_move]
        P2_DECIDE[🤖 Player 2<br/>Strategy.decide_move]
        
        P1_DECIDE --> P1_SEND[📥 P1 sends<br/>CHOOSE_PARITY_RESPONSE]
        P2_DECIDE --> P2_SEND[📥 P2 sends<br/>CHOOSE_PARITY_RESPONSE]
    end
    
    P1_SEND --> COLLECT
    P2_SEND --> COLLECT
    
    subgraph "Resolution Phase"
        COLLECT[📋 Referee collects<br/>both moves]
        
        COLLECT --> VALIDATE{Validate<br/>moves 1-5?}
        
        VALIDATE -->|Invalid| TIMEOUT{Timeout?}
        TIMEOUT -->|Yes| DEFAULT[Use default = 3]
        TIMEOUT -->|No| ERROR[❌ Handle Error]
        DEFAULT --> CALC
        
        VALIDATE -->|Valid| CALC[🧮 Calculate Sum]
        
        CALC --> PARITY{Sum % 2?}
        
        PARITY -->|"Odd (1,3,5,7,9)"| ODD_WINS[🎯 ODD Player Wins]
        PARITY -->|"Even (2,4,6,8,10)"| EVEN_WINS[🎯 EVEN Player Wins]
    end
    
    ODD_WINS --> UPDATE
    EVEN_WINS --> UPDATE
    
    subgraph "Result Broadcast"
        UPDATE[📊 Update Scores]
        UPDATE --> SEND_RESULTS[📤 Send ROUND_RESULT<br/>to both players]
    end
    
    SEND_RESULTS --> CHECK{Match<br/>Winner?}
    
    CHECK -->|"No (continue)"| START
    CHECK -->|"Yes (3 wins)"| FINISH([Match Complete])
```

### Summary: Complete Communication Flow

```mermaid
flowchart TB
    subgraph "1️⃣ STARTUP"
        START[CLI starts all agents]
    end
    
    subgraph "2️⃣ REGISTRATION"
        REF_REG[Referee registers]
        PLAYER_REG[Players register]
    end
    
    subgraph "3️⃣ LEAGUE START"
        GEN_SCHEDULE[Generate round-robin schedule]
    end
    
    subgraph "4️⃣ FOR EACH ROUND"
        ANNOUNCE[Round announcement]
        
        subgraph "Match Execution"
            INVITE[Send GAME_INVITE]
            ACCEPT[Receive GAME_JOIN_ACK]
            ROUNDS[Play rounds<br/>CHOOSE_PARITY_CALL/RESPONSE]
            RESULT[Send GAME_OVER]
        end
        
        REPORT[MATCH_RESULT_REPORT]
        UPDATE[LEAGUE_STANDINGS_UPDATE]
    end
    
    subgraph "5️⃣ COMPLETION"
        COMPLETE[LEAGUE_COMPLETED<br/>🏆 Champion declared]
    end
    
    START --> REF_REG
    REF_REG --> PLAYER_REG
    PLAYER_REG --> GEN_SCHEDULE
    GEN_SCHEDULE --> ANNOUNCE
    ANNOUNCE --> INVITE
    INVITE --> ACCEPT
    ACCEPT --> ROUNDS
    ROUNDS --> RESULT
    RESULT --> REPORT
    REPORT --> UPDATE
    UPDATE -->|More rounds| ANNOUNCE
    UPDATE -->|All done| COMPLETE
```

---

## 💬 Agent Communication

### Bidirectional MCP Communication

> **Key Concept**: Each agent has BOTH an MCP Server (receives requests) AND an MCP Client (makes requests to other agents)

```mermaid
graph LR
    subgraph "League Manager Agent"
        LM_S[📥 Server<br/>:8000]
        LM_C[📤 Client]
        LM_LOGIC[Logic]
        LM_S -.-> LM_LOGIC
        LM_C -.-> LM_LOGIC
    end
    
    subgraph "Referee Agent"
        REF_S[📥 Server<br/>:8001]
        REF_C[📤 Client]
        REF_LOGIC[Logic]
        REF_S -.-> REF_LOGIC
        REF_C -.-> REF_LOGIC
    end
    
    subgraph "Player 1 Agent"
        P1_S[📥 Server<br/>:8101]
        P1_C[📤 Client]
        P1_LOGIC[Logic]
        P1_S -.-> P1_LOGIC
        P1_C -.-> P1_LOGIC
    end
    
    subgraph "Player 2 Agent"
        P2_S[📥 Server<br/>:8102]
        P2_C[📤 Client]
        P2_LOGIC[Logic]
        P2_S -.-> P2_LOGIC
        P2_C -.-> P2_LOGIC
    end
    
    %% Registration flow
    P1_C -->|"1️⃣ register_player()"| LM_S
    P2_C -->|"1️⃣ register_player()"| LM_S
    LM_S -->|"2️⃣ {token}"| P1_C
    LM_S -->|"2️⃣ {token}"| P2_C
    
    %% Referee assignment
    LM_C -->|"3️⃣ start_match()"| REF_S
    
    %% Game invitations
    REF_C -->|"4️⃣ GAME_INVITE"| P1_S
    REF_C -->|"4️⃣ GAME_INVITE"| P2_S
    
    %% Move submissions
    P1_C -->|"5️⃣ MOVE_RESPONSE"| REF_S
    P2_C -->|"5️⃣ MOVE_RESPONSE"| REF_S
    
    %% Result reporting
    REF_C -->|"6️⃣ report_result()"| LM_S
```

### Message Routing Matrix

```mermaid
graph LR
    subgraph "Senders"
        S_LM[🏛️ League Manager]
        S_REF[⚖️ Referee]
        S_P[🤖 Player]
    end
    
    subgraph "Receivers"
        R_LM[🏛️ League Manager]
        R_REF[⚖️ Referee]
        R_P[🤖 Player]
    end
    
    S_LM -->|"ROUND_ANNOUNCEMENT<br/>start_match()"| R_REF
    S_LM -->|"REGISTER_RESPONSE<br/>STANDINGS_UPDATE<br/>LEAGUE_COMPLETED"| R_P
    
    S_REF -->|"MATCH_RESULT_REPORT"| R_LM
    S_REF -->|"GAME_INVITE<br/>GAME_START<br/>CHOOSE_PARITY_CALL<br/>ROUND_RESULT<br/>GAME_OVER"| R_P
    
    S_P -->|"REGISTER_REQUEST"| R_LM
    S_P -->|"GAME_JOIN_ACK<br/>CHOOSE_PARITY_RESPONSE"| R_REF
```

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
        +PlayerMeta player_meta
    }
    
    class PlayerMeta {
        +string display_name
        +string version
        +string[] game_types
        +string contact_endpoint
    }
    
    class LEAGUE_REGISTER_RESPONSE {
        +string status
        +string player_id
        +string auth_token
        +string reason
    }
    
    class REFEREE_REGISTER_REQUEST {
        +RefereeMeta referee_meta
    }
    
    class RefereeMeta {
        +string display_name
        +string version
        +string[] game_types
        +string contact_endpoint
        +int max_concurrent_matches
    }
    
    class REFEREE_REGISTER_RESPONSE {
        +string status
        +string referee_id
        +string auth_token
        +string reason
    }
    
    class GAME_INVITE {
        +string game_id
        +string match_id
        +string opponent_id
        +string assigned_role
        +int rounds_to_play
    }
    
    class CHOOSE_PARITY_CALL {
        +string match_id
        +string player_id
        +string opponent_id
        +int round_id
        +dict your_standings
        +string deadline
    }
    
    class CHOOSE_PARITY_RESPONSE {
        +string match_id
        +string player_id
        +string parity_choice
    }
    
    class GAME_OVER {
        +string match_id
        +string game_type
        +string status
        +string winner_player_id
        +int drawn_number
        +string number_parity
        +dict choices
    }
    
    class MATCH_RESULT_REPORT {
        +string league_id
        +int round_id
        +string match_id
        +string game_type
        +string winner_id
        +dict score
    }
    
    BaseMessage <|-- LEAGUE_REGISTER_REQUEST
    BaseMessage <|-- LEAGUE_REGISTER_RESPONSE
    BaseMessage <|-- REFEREE_REGISTER_REQUEST
    BaseMessage <|-- REFEREE_REGISTER_RESPONSE
    BaseMessage <|-- GAME_INVITE
    BaseMessage <|-- CHOOSE_PARITY_CALL
    BaseMessage <|-- CHOOSE_PARITY_RESPONSE
    BaseMessage <|-- GAME_OVER
    BaseMessage <|-- MATCH_RESULT_REPORT
    LEAGUE_REGISTER_REQUEST *-- PlayerMeta
    REFEREE_REGISTER_REQUEST *-- RefereeMeta
```

**Code Reference**: `src/common/protocol.py` → `MessageFactory`

### Message Timeouts

| Message Type | Timeout | Code Constant |
|--------------|---------|---------------|
| `REFEREE_REGISTER` | 10 seconds | `MessageTimeout.REFEREE_REGISTER` |
| `LEAGUE_REGISTER` | 10 seconds | `MessageTimeout.LEAGUE_REGISTER` |
| `GAME_JOIN_ACK` | 5 seconds | `MessageTimeout.GAME_JOIN_ACK` |
| `CHOOSE_PARITY` (Move) | 30 seconds | `MessageTimeout.CHOOSE_PARITY` |
| `GAME_OVER` | 5 seconds | `MessageTimeout.GAME_OVER` |
| `MATCH_RESULT_REPORT` | 10 seconds | `MessageTimeout.MATCH_RESULT_REPORT` |
| `LEAGUE_QUERY` | 10 seconds | `MessageTimeout.LEAGUE_QUERY` |
| Generic Response | 10 seconds | `MessageTimeout.GENERIC` |

**Code Reference**: `src/common/protocol.py` → `MessageTimeout`

---

## 🔀 State Machines

### Player Agent States

The player uses two state systems:
1. **AgentState** (lifecycle): `INIT → REGISTERED → ACTIVE → SHUTDOWN`
2. **GameSession.state** (per-game): `invited → accepted → making_move → awaiting_next → completed`

```mermaid
stateDiagram-v2
    [*] --> INIT: Create Player
    
    INIT --> REGISTERED: LEAGUE_REGISTER_RESPONSE ✓
    INIT --> SHUTDOWN: Registration failed
    
    REGISTERED --> ACTIVE: GAME_INVITE received
    REGISTERED --> SHUTDOWN: League ended
    
    ACTIVE --> SUSPENDED: Timeout / Error
    ACTIVE --> SHUTDOWN: League ended
    
    SUSPENDED --> ACTIVE: Recovered
    SUSPENDED --> SHUTDOWN: Max retries exceeded
    
    SHUTDOWN --> [*]
    
    note right of INIT: Agent started, not registered
    note right of REGISTERED: Has auth_token, waiting for games
    note right of ACTIVE: Participating in games
    note right of SUSPENDED: Temporarily unavailable
    note right of SHUTDOWN: Agent finished

    state "Game Session States" as GameSession {
        invited --> accepted: Accept invitation
        invited --> declined: Decline invitation
        accepted --> making_move: CHOOSE_PARITY_CALL
        making_move --> awaiting_next: Move submitted
        awaiting_next --> making_move: Next round
        awaiting_next --> completed: GAME_OVER
    }
```

**Code Reference**: `src/common/protocol.py` → `AgentState`, `src/agents/player.py` → `GameSession.state`

### Referee Agent States

```mermaid
stateDiagram-v2
    [*] --> IDLE: Create Referee
    
    IDLE --> WAITING_FOR_PLAYERS: Match assigned (start_match)
    
    WAITING_FOR_PLAYERS --> COLLECTING_CHOICES: Players ready
    WAITING_FOR_PLAYERS --> FINISHED: Timeout (forfeit)
    
    COLLECTING_CHOICES --> DRAWING_NUMBER: Both moves received
    COLLECTING_CHOICES --> COLLECTING_CHOICES: Timeout (use default)
    
    DRAWING_NUMBER --> COLLECTING_CHOICES: More rounds needed
    DRAWING_NUMBER --> FINISHED: Match complete
    
    FINISHED --> IDLE: Ready for next match
    
    IDLE --> [*]: League ended
    
    note right of IDLE: Ready to manage matches
    note right of WAITING_FOR_PLAYERS: Sent GAME_INVITE, awaiting ACK
    note right of COLLECTING_CHOICES: Sent CHOOSE_PARITY_CALL
    note right of DRAWING_NUMBER: Resolving round winner
    note right of FINISHED: Reporting result to League Manager
```

**Code Reference**: `src/agents/referee.py` → `RefereeState`

### League Manager States

```mermaid
stateDiagram-v2
    [*] --> REGISTRATION: Create League
    
    REGISTRATION --> REGISTRATION: Player/Referee registered
    REGISTRATION --> READY: Min players reached + start_league()
    
    READY --> IN_PROGRESS: start_next_round()
    
    IN_PROGRESS --> IN_PROGRESS: Round completed, more rounds
    IN_PROGRESS --> COMPLETED: All rounds finished
    
    COMPLETED --> [*]: League ended
    
    note right of REGISTRATION: Accepting player & referee registrations
    note right of READY: Schedule created, ready to start
    note right of IN_PROGRESS: Tournament running
    note right of COMPLETED: Champion determined
```

**Code Reference**: `src/agents/league_manager.py` → `LeagueState`

### Match States

```mermaid
stateDiagram-v2
    [*] --> SCHEDULED: Match created
    
    SCHEDULED --> INVITATIONS_SENT: GAME_INVITE sent
    
    INVITATIONS_SENT --> PLAYERS_READY: Both ACKs received
    INVITATIONS_SENT --> CANCELLED: Timeout
    
    PLAYERS_READY --> IN_PROGRESS: Game started
    
    IN_PROGRESS --> COMPLETED: Winner determined
    IN_PROGRESS --> CANCELLED: Error
    
    COMPLETED --> [*]
    CANCELLED --> [*]
```

**Code Reference**: `src/game/match.py` → `MatchState`

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
    
    ROUND --> CHOOSE[Both players choose<br/>number 1-10 secretly]
    
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

**Code Reference**: `src/game/odd_even.py` → `OddEvenGame`, `OddEvenRules`

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
        RANDOM[🎲 RandomStrategy<br/>Uniform random 1-10]
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

**Code Reference**: `src/agents/player.py` → `PlayerAgent.decide_move()`

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

**Code Reference**: `src/common/config.py` → `DEFAULT_PORTS`

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
- [Communication Flow Diagrams](./docs/COMMUNICATION_FLOW_DIAGRAM.md) - Detailed Mermaid diagrams
- [Command Reference](./docs/COMMAND_REFERENCE.md)

---

## 📄 License

MIT License

---

<div align="center">

**Built with ❤️ using Model Context Protocol**

*Last Updated: December 23, 2024*

</div>
