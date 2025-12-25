# MCP Multi-Agent Game League - Requirements Document

## 📋 Overview

Build an **MCP-based (Model Context Protocol) multi-agent game system** featuring a league of AI players competing against each other, orchestrated by a referee agent. The system must demonstrate proper client-server architecture following MCP standards.

---

## 🎓 Learning Objectives

By implementing this system, you will learn how to:

| # | Objective | Description |
|---|-----------|-------------|
| 1 | **Implement AI Agent** | Define and implement an autonomous AI agent |
| 2 | **Use Communication Protocol** | Understand and use a structured communication protocol (JSON schemas) |
| 3 | **Separation of Concerns** | Implement the principle of separation of concerns in software architecture |
| 4 | **Develop Game Strategy** | Develop a strategy for a competitive game |
| 5 | **Distributed Systems** | Participate in a distributed system of agents |

---

## 🎯 Game Structure

### League Definition
> **"A league is a competitive framework where multiple participants compete against each other according to defined rules."**
> 
> In this context, the league organizes competition between **different AI agents**.

### League Format: Round-Robin
**"Everyone plays against everyone"** - Each agent must play against all other agents in the league.

### League Configuration
| Component | Count | Description |
|-----------|-------|-------------|
| **Players** | 4+ | AI agents (with different strategies) |
| **Referee** | 1 | Agent that manages game rules and scoring |
| **Games per Round** | 2 | Each round consists of 2 parallel games |
| **League** | 1 | Single league managing all matches |

### Three Architectural Layers of the League

| Layer | Role | Responsibilities |
|-------|------|------------------|
| **League Layer** | Managing overall competition | Player registration, game scheduling, ranking/standings calculation |
| **Referee Layer** | Managing a single game | Start game, validate moves, declare winner, game state management |
| **Game Layer** | Specific game rules | Move legality check, victory condition evaluation, game-specific logic |

### 🔑 Core Principle: Separation of Concerns

> **IMPORTANT**: The League Layer and Referee Layer are **NOT dependent** on the specific game. 
> You can replace the "Odd/Even" game with Tic-Tac-Toe, Chess, or any other game - **WITHOUT changing the general protocol**.

**Implication**: If you build an agent that correctly speaks "the protocol language" (MCP), it will be able to participate in **any future league**, regardless of the specific game.

### 🎮 The Game: Odd/Even

The system uses the **"Odd/Even"** game as the specific game implementation. This is a simple game that allows focus on the architecture rather than complex game logic.

**Game Rules** (typical Odd/Even):
- Two players each choose a number (usually 1-5 fingers)
- Players reveal simultaneously
- Sum is calculated
- One player wins if sum is ODD, other wins if sum is EVEN
- Can be played in rounds for best-of-N format

### Agent Architecture (Player Side)
Each AI agent has three components:
1. **Sensors**: Input processing - receiving game state
2. **Decision Model**: The algorithm that chooses the next move (LLM-based)
3. **Actuators**: JSON messages sent back to referee (the chosen move)

### Scalability Mindset
> ⚠️ **Important**: Design as if scaling to **100,000 players** and **100,000 leagues**. The architecture must be modular and scalable, not just functional.

---

## 🏗️ Architecture Requirements

### MCP Protocol Fundamentals

#### What is MCP?
> **Model Context Protocol (MCP)** is a standard communication protocol for AI agents. It defines how agents communicate with each other using structured messages.

#### Analogy
> Think of MCP like the **HTTP protocol** for the internet. Just as HTTP defines how browsers and servers communicate, **MCP defines how AI agents communicate**.

#### Communication Structure
> **Every agent in the system implements a small MCP server that listens for requests.**

The system must implement the **three MCP primitives**:

| Primitive | Type | Description |
|-----------|------|-------------|
| **Resources** | Read-only | Data sources (databases, files, images) that can be read but not modified |
| **Tools** | Active | Operations that perform actions and return results |
| **Prompts** | Templates | Predefined templates to help agents understand request formats |

### Transport Layers
The system uses:
- **HTTP over localhost** - Each agent runs an MCP server on localhost with different ports
- **Endpoint**: `/mcp` on each server
- **Method**: HTTP POST
- **Protocol**: JSON-RPC 2.0

### Port Configuration 

| Component | URL |
|-----------|-----|
| **League Manager** | `http://localhost:8000/mcp` |
| **Referee** | `http://localhost:8001/mcp` |
| **Player 1** | `http://localhost:8101/mcp` |
| **Player 2** | `http://localhost:8102/mcp` |
| **Player 3** | `http://localhost:8103/mcp` |
| **Player 4** | `http://localhost:8104/mcp` |

> **Note**: Players use 81XX port range, system components use 80XX range

### Message Format
- All communication via **JSON-RPC 2.0** format
- HTTP POST requests to `/mcp` endpoint
- Proper serialization/deserialization layer

---

## 📨 Protocol Message Schema (Chapter 2)

### Protocol Principles

| Principle | Description |
|-----------|-------------|
| **Structured Messages** | Every message is a JSON object with a fixed structure |
| **Required & Optional Fields** | Some fields are required, others are optional |
| **Unique Identification** | Every league, round, game, and player has a unique ID |
| **Unambiguous Status** | System is always in a well-defined state |

### Basic Message Structure - Required Fields

**Every message MUST include these fields:**

```json
{
  "protocol": "league.v1",
  "message_type": "...",
  "league_id": "...",
  "round_id": 1,
  "match_id": "R1M3",
  "conversation_id": "uuid-or-similar",
  "sender": "league_manager | referee | player:<player_id>",
  "timestamp": "ISO-8601"
}
```

### Field Specifications

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `protocol` | string | **MUST be exactly `"league.v1"`** | `"league.v1"` |
| `message_type` | string | Type of message (see message types) | `"game_start"` |
| `league_id` | string | Unique league identifier | `"league_2024_01"` |
| `round_id` | integer | Current round number | `1` |
| `match_id` | string | Match identifier (format: R{round}M{match}) | `"R1M3"` |
| `conversation_id` | string | UUID for tracking conversation | `"550e8400-e29b..."` |
| `sender` | string | Who sent the message | `"referee"` or `"player:P1"` |
| `timestamp` | string | ISO-8601 formatted timestamp | `"2024-12-12T10:30:00Z"` |

### ⛔ Critical: Protocol Field Validation

> **The `protocol` field MUST be EXACTLY `"league.v1"`**
> 
> Any other value = **MESSAGE REJECTED**
> 
> This is the version compatibility checking mechanism.

---

## 🔄 League Lifecycle Messages

### Stage 1: Player Registration

#### LEAGUE_REGISTER_REQUEST (Player → League)

```json
{
  "protocol": "league.v1",
  "message_type": "LEAGUE_REGISTER_REQUEST",
  "league_id": "...",
  "conversation_id": "uuid",
  "sender": "player:<player_id>",
  "timestamp": "ISO-8601",
  "player_meta": {
    "display_name": "Agent Alpha",
    "version": "1.0.0",
    "game_types": ["even_odd"],
    "contact_endpoint": "mcp://player-alpha"
  }
}
```

| Field | Description |
|-------|-------------|
| `display_name` | Human-readable name for your agent |
| `version` | Your agent's version |
| `game_types` | Array of supported games - **MUST be `["even_odd"]`** |
| `contact_endpoint` | MCP endpoint where your agent listens |

#### LEAGUE_REGISTER_RESPONSE (League → Player)

```json
{
  "protocol": "league.v1",
  "message_type": "LEAGUE_REGISTER_RESPONSE",
  "league_id": "...",
  "conversation_id": "uuid",
  "sender": "league_manager",
  "timestamp": "ISO-8601",
  "status": "ACCEPTED",
  "player_id": "P07",
  "reason": "optional - only if REJECTED"
}
```

| Field | Description |
|-------|-------------|
| `status` | `"ACCEPTED"` or `"REJECTED"` |
| `player_id` | Your assigned player ID (e.g., "P07") |
| `reason` | Only provided if status is REJECTED |

> ⚠️ **IMPORTANT**: `game_types` MUST be exactly `["even_odd"]` for the current implementation!

---

## 🔧 Client Architecture (MCP Client)

The client must contain and manage these core components:

### 1. Session Manager
```
┌─────────────────────────────────────┐
│         Session Manager             │
├─────────────────────────────────────┤
│ • Track active sessions             │
│ • Add/remove sessions               │
│ • Handle multiple concurrent        │
│   connections to different servers  │
└─────────────────────────────────────┘
```

**Requirements:**
- [ ] Maintain list of active sessions
- [ ] Support connecting to multiple servers simultaneously
- [ ] Clean session termination and resource cleanup

### 2. Tools Registry
```
┌─────────────────────────────────────┐
│         Tools Registry              │
├─────────────────────────────────────┤
│ • Discover available tools          │
│ • Store tool metadata               │
│ • Namespace management              │
│   (server_name.tool_name)           │
└─────────────────────────────────────┘
```

**Requirements:**
- [ ] Collect tools from all connected servers
- [ ] Handle **name collisions** using namespace format: `server_name.tool_name`
- [ ] Provide unified tool list to LLM

### 3. Message Queue
```
┌─────────────────────────────────────┐
│         Message Queue               │
├─────────────────────────────────────┤
│ • Queue incoming/outgoing messages  │
│ • Priority management               │
│ • Rate limiting                     │
└─────────────────────────────────────┘
```

**Requirements:**
- [ ] FIFO queue with priority support
- [ ] Handle high-throughput scenarios
- [ ] Urgent messages can bypass queue

### 4. Resource Manager
```
┌─────────────────────────────────────┐
│        Resource Manager             │
├─────────────────────────────────────┤
│ • Track available resources         │
│ • Subscription mechanism            │
│ • Cache management                  │
└─────────────────────────────────────┘
```

**Requirements:**
- [ ] Know which databases/files are available
- [ ] **Subscription model** for real-time updates (no polling)
- [ ] Cache resources to reduce network traffic

### 5. Connection Manager
```
┌─────────────────────────────────────┐
│       Connection Manager            │
├─────────────────────────────────────┤
│ • Connect/Disconnect handling       │
│ • Heartbeat mechanism               │
│ • Retry logic                       │
└─────────────────────────────────────┘
```

**Requirements:**
- [ ] Manage connection lifecycle
- [ ] **Heartbeat** - periodic health checks
- [ ] **Retry logic** with exponential backoff + jitter

### 6. Transport Layer
```
┌─────────────────────────────────────┐
│        Transport Layer              │
├─────────────────────────────────────┤
│ • JSON serialization                │
│ • Protocol abstraction              │
│ • HTTP/STDIO support                │
└─────────────────────────────────────┘
```

---

## 🖥️ Server Architecture (MCP Server)

### Server Responsibilities
- [ ] Accept and authenticate connections
- [ ] Expose available tools and resources
- [ ] Execute business logic
- [ ] Validate inputs and protect resources

### Tool Exposure
Each server must expose its tools via the standard MCP `tools/list` response.

---

## 🔄 Communication Flow

### Initialization Sequence
```
┌────────┐                    ┌────────┐
│ Client │                    │ Server │
└───┬────┘                    └───┬────┘
    │                             │
    │  1. Initialize (handshake)  │
    │ ─────────────────────────►  │
    │                             │
    │  2. Server Info Response    │
    │ ◄─────────────────────────  │
    │                             │
    │  3. Request Tools List      │
    │ ─────────────────────────►  │
    │                             │
    │  4. Tools List Response     │
    │ ◄─────────────────────────  │
    │                             │
```

### Tool Execution Loop
```
┌──────────┐     ┌────────┐     ┌────────┐
│   User   │     │ Client │     │ Server │
└────┬─────┘     └───┬────┘     └───┬────┘
     │               │               │
     │   Query       │               │
     │ ─────────────►│               │
     │               │               │
     │               │  Tool Call    │
     │               │ ─────────────►│
     │               │               │
     │               │  Result       │
     │               │ ◄─────────────│
     │               │               │
     │   Response    │               │
     │ ◄─────────────│               │
     │               │               │
```

> ⚠️ **Critical**: Implement **maximum iteration limit** on loops to prevent infinite execution!

---

## ⚠️ Error Handling

### Error Categories

| Type | Description | Strategy |
|------|-------------|----------|
| **Transient** | Network issues, temporary overload | Retry with backoff |
| **Permanent** | Missing file, permission denied | Fail gracefully, no retry |
| **Timeout** | Response took too long | Increase timeout, retry |

### Recovery Strategies

1. **Exponential Backoff with Jitter**
```python
delay = min(base_delay * (2 ** attempt) + random_jitter, max_delay)
```
- Prevents thundering herd problem
- Jitter ensures multiple clients don't retry simultaneously

2. **Circuit Breaker**
- Stop calling failed servers temporarily
- Prevent cascade failures

3. **Fallback**
- Use cached data
- Route to alternative server

### Exception Handling
- [ ] Wrap all operations in try-catch
- [ ] Comprehensive logging
- [ ] Meaningful error messages for debugging

---

## 📊 Progress Tracking

For long-running operations:

- [ ] Generate unique **progress token** per request
- [ ] Server sends async progress updates
- [ ] Client displays progress to user
- [ ] Prevent "is the system stuck?" uncertainty

---

## 📝 Subscription Mechanism

For resources that update over time:

```
┌────────┐                         ┌────────┐
│ Client │                         │ Server │
└───┬────┘                         └───┬────┘
    │                                  │
    │  Subscribe (resource URI)        │
    │ ────────────────────────────────►│
    │                                  │
    │  Notification (on change)        │
    │ ◄────────────────────────────────│
    │                                  │
    │  Notification (on change)        │
    │ ◄────────────────────────────────│
    │                                  │
```

**Use Cases:**
- Log monitoring
- Database updates
- Game state changes

---

## 🔐 Security Requirements

1. **Sandbox Environment**
   - Run in Docker containers
   - Limit file system access
   - Define damage boundaries

2. **Input Validation**
   - Validate all inputs at system boundaries
   - Sanitize user inputs and external API responses

3. **Permission Control**
   - Tools should not perform unauthorized actions
   - Implement approval mechanism for sensitive operations

> ⚠️ **Warning**: Active tools can execute operations on your system. Be cautious of prompt injection attacks hidden in web pages or data sources.

---

## 🔀 Multi-Server Architecture

### Star Topology
```
           ┌──────────┐
           │ Server 1 │
           └────┬─────┘
                │
┌──────────┐    │    ┌──────────┐
│ Server 2 ├────┼────┤  Client  │
└──────────┘    │    └──────────┘
                │
           ┌────┴─────┐
           │ Server 3 │
           └──────────┘
```

### Requirements
- [ ] Single client connects to multiple servers
- [ ] Unified resource/tool view for LLM
- [ ] Smart routing to appropriate server
- [ ] Namespace collision prevention

---

## 🧪 Concurrency & Synchronization

### Thread Safety
- [ ] Use **Mutex** for shared resource access
- [ ] Implement proper locking mechanisms
- [ ] Consider **async/await** patterns with `asyncio`

### Multi-processing Considerations
- [ ] Heartbeat can run as background thread
- [ ] Message queue may need thread-safe implementation
- [ ] Session management across threads

---

## 📁 Recommended Project Structure

```
MCP_Multi_Agent_Game/
├── src/
│   ├── client/
│   │   ├── __init__.py
│   │   ├── mcp_client.py        # Main client implementation
│   │   ├── session_manager.py   # Session management
│   │   ├── tool_registry.py     # Tools registration
│   │   ├── message_queue.py     # Message queue handling
│   │   ├── resource_manager.py  # Resource management
│   │   ├── connection_manager.py # Connection handling
│   │   └── transport.py         # Transport layer
│   │
│   ├── server/
│   │   ├── __init__.py
│   │   ├── mcp_server.py        # Main server implementation
│   │   ├── tools/               # Tool implementations
│   │   └── resources/           # Resource definitions
│   │
│   ├── game/
│   │   ├── __init__.py
│   │   ├── player.py            # Player agent
│   │   ├── referee.py           # Referee agent
│   │   ├── league.py            # League management
│   │   └── match.py             # Match logic
│   │
│   └── common/
│       ├── __init__.py
│       ├── config.py            # Configuration
│       ├── logger.py            # Logging
│       └── exceptions.py        # Custom exceptions
│
├── config/
│   └── servers.json             # Server configurations
│
├── tests/
│   ├── test_client.py
│   ├── test_server.py
│   └── test_game.py
│
├── docs/
│   ├── architecture.md          # Architecture documentation
│   └── PRD.md                   # Product Requirements Document
│
├── requirements.txt             # Python dependencies
├── README.md                    # Project overview
└── REQUIREMENTS.md              # This file
```

---

## 📦 Required Dependencies

```txt
mcp                    # MCP protocol implementation
httpx                  # HTTP client
aiohttp                # Async HTTP
asyncio                # Async operations
pytest                 # Testing
pytest-asyncio         # Async testing
```

---

## ✅ Grading Criteria (from lecture)

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

## 🎮 Game Implementation Notes

### Referee Agent Responsibilities

The referee manages a **single game between two players**:

| # | Responsibility | Description |
|---|----------------|-------------|
| 1 | **Send Invitations** | Send game invitations to both players |
| 2 | **Manage Handshake** | Coordinate the handshake between players |
| 3 | **Collect & Validate Moves** | Collect moves from players and validate them |
| 4 | **Declare Results** | Announce winner and report results to league |

### Player Agent Responsibilities

**This is what YOU will build:**

| # | Responsibility | Description |
|---|----------------|-------------|
| 1 | **Register to League** | Send `LEAGUE_REGISTER_REQUEST` to join |
| 2 | **Respond to Game Invitations** | Accept/handle invitations from referee |
| 3 | **Execute Moves** | Make moves according to YOUR strategy |
| 4 | **Receive Results & Update State** | Process results, update internal state |

> 💡 **Key Insight**: Your strategy is what you program! The LLM or algorithm you design will determine how your agent plays.

### League Manager Responsibilities

| # | Responsibility | Description |
|---|----------------|-------------|
| 1 | **Player Registration** | Accept and track player registrations |
| 2 | **Schedule Matches** | Create game schedule (round-robin) |
| 3 | **Track Standings** | Maintain league table |
| 4 | **Manage Rounds** | Coordinate round progression |

---

## 📌 Key Takeaways (Chapter 1 Summary)

| Concept | Definition |
|---------|------------|
| **AI Agent** | Autonomous software entity that receives information and performs actions |
| **Game League** | Organizes competition between agents according to defined rules |
| **Architecture** | Separates between League, Referee, and Game layers |
| **MCP Protocol** | Enables standard communication between agents |
| **Implementation** | Two stages: local development → class competition |

### Core Principles from Lecture:

1. **"The client coordinates, the server executes"** - Core principle
2. **Plan architecture BEFORE coding** - Draw diagrams first
3. **Think at scale** - Design for 100K, implement for 4
4. **Modular components** - Each module has clear responsibility
5. **Proper error handling** - Systems must recover gracefully
6. **Security first** - Sandbox everything, validate inputs

---

## 📅 Development Phases

### Stage 1: Private League (Local Development)

In this stage, develop and test your agent locally:

| Task | Description |
|------|-------------|
| **Run Local League** | Set up the complete league infrastructure on your computer |
| **Test Against Simple Agents** | Practice against random or deterministic dummy agents |
| **Debug & Improve** | Fix bugs and refine your agent's strategy |

**Deliverables for Stage 1:**
- [ ] Working MCP server for your agent
- [ ] Local league manager and referee
- [ ] At least 2 dummy agents for testing
- [ ] Passing all local tests

### Stage 2: Class League (Competition)

After your agent is ready:

| Task | Description |
|------|-------------|
| **Submit Agent** | Submit your agent to the central class league |
| **Compete (One vs. All)** | Your agent plays against ALL other agents |
| **Grading** | **Your grade is determined by your position in the league table** |

**Deliverables for Stage 2:**
- [ ] Production-ready agent that follows MCP protocol
- [ ] Agent can connect to external league server
- [ ] Agent handles all error cases gracefully

---

## 🚨 CRITICAL WARNING

> ⛔ **If your agent does not speak the protocol language EXACTLY as defined - it will be DISQUALIFIED.**
>
> - ❌ No half-compatibility
> - ❌ No "almost correct"  
> - ✅ The protocol is a **BINDING CONTRACT**

**This means:**
- Your JSON-RPC messages must be **exactly** formatted
- All required fields must be present
- All responses must follow the exact schema
- Any deviation = **automatic disqualification**

---

## 🚀 Getting Started

1. Set up Python environment with required dependencies
2. Design architecture diagrams
3. Implement core MCP client components
4. Implement MCP server with game tools
5. Build game logic (players, referee, league)
6. Create dummy agents for local testing (Stage 1)
7. Add error handling and recovery
8. Write tests
9. Document everything
10. Submit to class league (Stage 2)

---

*Last Updated: December 12, 2025*

