# Architecture Overview

> **Production-Grade MCP Multi-Agent Game League System Architecture**
>
> This document provides comprehensive architecture diagrams and design decisions for the MCP-based multi-agent game system.

---

## Table of Contents

- [Three-Layer Architecture](#three-layer-league-architecture-from-course-materials)
- [System Architecture](#system-architecture-diagram)
- [Client Architecture](#client-architecture-layers)
- [Session & Connection Management](#session--connection-management)
- [Message Queue](#message-queue-architecture)
- [Tool Registry](#tool-registry--namespace-management)
- [Error Handling](#error-handling--recovery)
- [Game Flow](#game-flow-architecture)
- [Match Flow](#single-match-flow)
- [Resource Subscriptions](#resource-subscription-flow)
- [Security](#security-architecture)
- [Progress Tracking](#progress-tracking)
- [Implementation Details](#implementation-details)

---

## Three-Layer League Architecture (From Course Materials)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                 │
│  ╔═══════════════════════════════════════════════════════════════════════════╗ │
│  ║                           LEAGUE LAYER                                    ║ │
│  ║                                                                           ║ │
│  ║  Role: Managing the overall competition                                   ║ │
│  ║                                                                           ║ │
│  ║  • Player registration                                                    ║ │
│  ║  • Creating game schedule                                                 ║ │
│  ║  • Ranking/standings calculation                                          ║ │
│  ║                                                                           ║ │
│  ╚═══════════════════════════════════════════════════════════════════════════╝ │
│                                      │                                          │
│                                      ▼                                          │
│  ╔═══════════════════════════════════════════════════════════════════════════╗ │
│  ║                          REFEREE LAYER                                    ║ │
│  ║                                                                           ║ │
│  ║  Role: Managing a single game                                             ║ │
│  ║                                                                           ║ │
│  ║  • Starting game                                                          ║ │
│  ║  • Validating moves                                                       ║ │
│  ║  • Declaring winner                                                       ║ │
│  ║                                                                           ║ │
│  ╚═══════════════════════════════════════════════════════════════════════════╝ │
│                                      │                                          │
│                                      ▼                                          │
│  ╔═══════════════════════════════════════════════════════════════════════════╗ │
│  ║                            GAME LAYER                                     ║ │
│  ║                                                                           ║ │
│  ║  Role: Specific game rules                                                ║ │
│  ║                                                                           ║ │
│  ║  • Move legality check                                                    ║ │
│  ║  • Determining victory conditions                                         ║ │
│  ║                                                                           ║ │
│  ╚═══════════════════════════════════════════════════════════════════════════╝ │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AGENTIC GAME SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                           LLM LAYER (Brain)                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │  Player 1   │  │  Player 2   │  │  Player 3   │  │  Player 4   │    │   │
│  │  │    Agent    │  │    Agent    │  │    Agent    │  │    Agent    │    │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │   │
│  │         │                │                │                │           │   │
│  │         └────────────────┼────────────────┼────────────────┘           │   │
│  │                          │                │                            │   │
│  │                    ┌─────┴────────────────┴─────┐                      │   │
│  │                    │      REFEREE AGENT         │                      │   │
│  │                    │  (Game Rules & Scoring)    │                      │   │
│  │                    └─────────────┬──────────────┘                      │   │
│  └──────────────────────────────────┼──────────────────────────────────────┘   │
│                                     │                                          │
│  ┌──────────────────────────────────┼──────────────────────────────────────┐   │
│  │                     MCP CLIENT INTERFACE                                │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │                      CLIENT CORE                                 │   │   │
│  │  │                                                                  │   │   │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │   │   │
│  │  │  │   Session    │  │    Tool      │  │      Message         │  │   │   │
│  │  │  │   Manager    │  │   Registry   │  │       Queue          │  │   │   │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │   │   │
│  │  │                                                                  │   │   │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │   │   │
│  │  │  │  Resource    │  │  Connection  │  │      Transport       │  │   │   │
│  │  │  │   Manager    │  │   Manager    │  │       Layer          │  │   │   │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────┬──────────────────────────────────────┘   │
│                                     │                                          │
│                          JSON-RPC (HTTP/STDIO)                                 │
│                                     │                                          │
│  ┌──────────────────────────────────┼──────────────────────────────────────┐   │
│  │                        MCP SERVERS                                      │   │
│  │                                  │                                      │   │
│  │     ┌────────────────────────────┼────────────────────────────┐        │   │
│  │     │                            │                            │        │   │
│  │  ┌──┴───────────┐  ┌─────────────┴──────────┐  ┌─────────────┴──┐     │   │
│  │  │ GAME SERVER  │  │    LEAGUE SERVER       │  │  DATA SERVER   │     │   │
│  │  │              │  │                        │  │                │     │   │
│  │  │ Tools:       │  │ Tools:                 │  │ Resources:     │     │   │
│  │  │ • make_move  │  │ • get_standings        │  │ • player_stats │     │   │
│  │  │ • get_state  │  │ • schedule_match       │  │ • game_history │     │   │
│  │  │ • validate   │  │ • update_scores        │  │ • league_data  │     │   │
│  │  │              │  │ • get_next_match       │  │                │     │   │
│  │  └──────────────┘  └────────────────────────┘  └────────────────┘     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Client Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM (Decision Maker)                     │  Layer 5
│              Makes decisions, initiates actions             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Client Interface (API)                    │  Layer 4
│           API that the LLM model works against              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      System Core                            │  Layer 3
│         Session Manager + Tool Registry + Resources         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Message Processing                        │  Layer 2
│              JSON serialization/deserialization             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Transport Layer                          │  Layer 1
│                  HTTP / STDIO communication                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   MCP SERVER    │
                    └─────────────────┘
```

---

## Session & Connection Management

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        CONNECTION MANAGER                                │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      SESSION POOL                                  │ │
│  │                                                                    │ │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │ │
│  │   │  Session 1   │  │  Session 2   │  │  Session 3   │           │ │
│  │   │  Server: A   │  │  Server: B   │  │  Server: C   │           │ │
│  │   │  Port: 8001  │  │  Port: 8002  │  │  Port: 8003  │           │ │
│  │   │  Status: ✓   │  │  Status: ✓   │  │  Status: ✗   │           │ │
│  │   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │ │
│  │          │                 │                 │                    │ │
│  └──────────┼─────────────────┼─────────────────┼────────────────────┘ │
│             │                 │                 │                      │
│  ┌──────────┼─────────────────┼─────────────────┼────────────────────┐ │
│  │          ▼                 ▼                 ▼                    │ │
│  │   ┌─────────────────────────────────────────────────────────┐    │ │
│  │   │                   HEARTBEAT MONITOR                     │    │ │
│  │   │        (Background Thread - Periodic Health Check)      │    │ │
│  │   └─────────────────────────────────────────────────────────┘    │ │
│  │                                                                   │ │
│  │   ┌─────────────────────────────────────────────────────────┐    │ │
│  │   │                     RETRY HANDLER                       │    │ │
│  │   │         (Exponential Backoff + Jitter Logic)            │    │ │
│  │   └─────────────────────────────────────────────────────────┘    │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Message Queue Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          MESSAGE QUEUE                                  │
│                                                                         │
│   INCOMING                                          OUTGOING            │
│   ┌─────────┐                                      ┌─────────┐         │
│   │ Message │ ──┐                              ┌── │ Message │         │
│   └─────────┘   │                              │   └─────────┘         │
│   ┌─────────┐   │    ┌──────────────────┐     │   ┌─────────┐         │
│   │ Message │ ──┼───►│  PRIORITY QUEUE  │─────┼──►│ Message │         │
│   └─────────┘   │    │                  │     │   └─────────┘         │
│   ┌─────────┐   │    │  ┌────────────┐  │     │   ┌─────────┐         │
│   │ Message │ ──┘    │  │  URGENT    │  │     └──►│ Message │         │
│   └─────────┘        │  │  Priority  │  │         └─────────┘         │
│                      │  └────────────┘  │                              │
│                      │  ┌────────────┐  │                              │
│                      │  │   HIGH     │  │                              │
│                      │  │  Priority  │  │                              │
│                      │  └────────────┘  │                              │
│                      │  ┌────────────┐  │                              │
│                      │  │  NORMAL    │  │                              │
│                      │  │  Priority  │  │                              │
│                      │  └────────────┘  │                              │
│                      └──────────────────┘                              │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    THREAD SAFETY (Mutex/Lock)                   │  │
│   └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Tool Registry & Namespace Management

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TOOL REGISTRY                                   │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    NAMESPACE FORMAT                             │  │
│   │                                                                 │  │
│   │              server_name.tool_name                              │  │
│   │                                                                 │  │
│   │   Examples:                                                     │  │
│   │   • game_server.make_move                                       │  │
│   │   • game_server.get_state                                       │  │
│   │   • league_server.get_standings                                 │  │
│   │   • data_server.query_stats                                     │  │
│   │                                                                 │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    UNIFIED TOOL LIST                            │  │
│   │                                                                 │  │
│   │  ┌───────────────────────────────────────────────────────────┐ │  │
│   │  │  Tool Name                    │ Server    │ Description   │ │  │
│   │  ├───────────────────────────────┼───────────┼───────────────┤ │  │
│   │  │  game_server.make_move        │ game      │ Make a move   │ │  │
│   │  │  game_server.get_state        │ game      │ Get game st.  │ │  │
│   │  │  league_server.get_standings  │ league    │ Get rankings  │ │  │
│   │  │  league_server.schedule_match │ league    │ Schedule game │ │  │
│   │  └───────────────────────────────┴───────────┴───────────────┘ │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│                      COLLISION PREVENTION                               │
│   If two servers expose "get_state":                                   │
│   • game_server.get_state    ← Different tools!                        │
│   • data_server.get_state    ←                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Error Handling & Recovery

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ERROR HANDLING FLOW                                │
│                                                                         │
│   ┌─────────┐                                                          │
│   │  Error  │                                                          │
│   │ Occurs  │                                                          │
│   └────┬────┘                                                          │
│        │                                                                │
│        ▼                                                                │
│   ┌─────────────────┐                                                  │
│   │ Classify Error  │                                                  │
│   └────────┬────────┘                                                  │
│            │                                                            │
│    ┌───────┼───────────────────────┐                                   │
│    │       │                       │                                    │
│    ▼       ▼                       ▼                                    │
│ ┌──────┐ ┌──────────┐        ┌──────────┐                             │
│ │Trans-│ │Permanent │        │ Timeout  │                             │
│ │ient  │ │          │        │          │                             │
│ └──┬───┘ └────┬─────┘        └────┬─────┘                             │
│    │          │                   │                                    │
│    ▼          ▼                   ▼                                    │
│ ┌──────────┐ ┌──────────┐  ┌─────────────┐                            │
│ │  Retry   │ │   Fail   │  │  Increase   │                            │
│ │  with    │ │ Graceful │  │  Timeout &  │                            │
│ │ Backoff  │ │  (log)   │  │   Retry     │                            │
│ └────┬─────┘ └──────────┘  └──────┬──────┘                            │
│      │                            │                                    │
│      ▼                            │                                    │
│ ┌──────────────────┐              │                                    │
│ │ Exponential      │◄─────────────┘                                    │
│ │ Backoff + Jitter │                                                   │
│ │                  │                                                   │
│ │ delay = min(     │                                                   │
│ │   base * 2^n     │                                                   │
│ │   + jitter,      │                                                   │
│ │   max_delay      │                                                   │
│ │ )                │                                                   │
│ └──────────────────┘                                                   │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    CIRCUIT BREAKER                              │  │
│   │                                                                 │  │
│   │   After N failures → Stop calling failed server                │  │
│   │   Wait for cooldown → Try again                                │  │
│   │   Success → Reset failure count                                │  │
│   └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Game Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LEAGUE GAME FLOW                                │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                      LEAGUE MANAGER                             │  │
│   │                                                                 │  │
│   │   • Schedule matches                                            │  │
│   │   • Track standings                                             │  │
│   │   • Manage rounds                                               │  │
│   └───────────────────────────┬─────────────────────────────────────┘  │
│                               │                                         │
│                               ▼                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                        ROUND N                                  │  │
│   │                                                                 │  │
│   │   ┌───────────────────┐      ┌───────────────────┐             │  │
│   │   │     MATCH 1       │      │     MATCH 2       │             │  │
│   │   │                   │      │                   │             │  │
│   │   │  Player 1    vs   │      │  Player 3    vs   │             │  │
│   │   │  Player 2         │      │  Player 4         │             │  │
│   │   │                   │      │                   │             │  │
│   │   │  ┌─────────────┐  │      │  ┌─────────────┐  │             │  │
│   │   │  │   REFEREE   │  │      │  │   REFEREE   │  │             │  │
│   │   │  │  Validates  │  │      │  │  Validates  │  │             │  │
│   │   │  │  Scores     │  │      │  │  Scores     │  │             │  │
│   │   │  └─────────────┘  │      │  └─────────────┘  │             │  │
│   │   └───────────────────┘      └───────────────────┘             │  │
│   │              │                          │                       │  │
│   │              └──────────┬───────────────┘                       │  │
│   │                         │                                       │  │
│   │                         ▼                                       │  │
│   │              ┌──────────────────┐                               │  │
│   │              │  Update Scores   │                               │  │
│   │              │  Update Standings│                               │  │
│   │              └──────────────────┘                               │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                               │                                         │
│                               ▼                                         │
│                    Continue to Round N+1                               │
│                               │                                         │
│                               ▼                                         │
│                    ┌──────────────────┐                                │
│                    │ LEAGUE COMPLETE  │                                │
│                    │ Declare Champion │                                │
│                    └──────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Single Match Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MATCH FLOW                                      │
│                                                                         │
│     ┌──────────┐                              ┌──────────┐             │
│     │ Player A │                              │ Player B │             │
│     └────┬─────┘                              └────┬─────┘             │
│          │                                         │                    │
│          │         ┌─────────────────┐            │                    │
│          │         │    REFEREE      │            │                    │
│          │         └────────┬────────┘            │                    │
│          │                  │                      │                    │
│          │    Game Start    │    Game Start        │                    │
│          │◄─────────────────┤───────────────────► │                    │
│          │                  │                      │                    │
│   ┌──────┴──────┐          │              ┌───────┴──────┐            │
│   │ Receive     │          │              │ Receive      │            │
│   │ Game State  │          │              │ Game State   │            │
│   └──────┬──────┘          │              └───────┬──────┘            │
│          │                  │                      │                    │
│   ┌──────┴──────┐          │              ┌───────┴──────┐            │
│   │ LLM Decides │          │              │ LLM Decides  │            │
│   │ Move        │          │              │ Move         │            │
│   └──────┬──────┘          │              └───────┬──────┘            │
│          │                  │                      │                    │
│          │    Submit Move   │                      │                    │
│          │─────────────────►│                      │                    │
│          │                  │                      │                    │
│          │                  │◄─────────────────────│                    │
│          │                  │     Submit Move      │                    │
│          │                  │                      │                    │
│          │           ┌──────┴──────┐              │                    │
│          │           │  Validate   │              │                    │
│          │           │    Moves    │              │                    │
│          │           └──────┬──────┘              │                    │
│          │                  │                      │                    │
│          │           ┌──────┴──────┐              │                    │
│          │           │   Update    │              │                    │
│          │           │   State     │              │                    │
│          │           └──────┬──────┘              │                    │
│          │                  │                      │                    │
│          │◄─────────────────┤───────────────────►│                    │
│          │   New State      │    New State        │                    │
│          │                  │                      │                    │
│          │         [Repeat until game ends]       │                    │
│          │                  │                      │                    │
│          │◄─────────────────┤───────────────────►│                    │
│          │   Game Result    │    Game Result      │                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Resource Subscription Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    RESOURCE SUBSCRIPTION                                │
│                                                                         │
│   ┌────────┐                                    ┌────────┐             │
│   │ Client │                                    │ Server │             │
│   └───┬────┘                                    └───┬────┘             │
│       │                                             │                   │
│       │     Subscribe(resource_uri)                 │                   │
│       │────────────────────────────────────────────►│                   │
│       │                                             │                   │
│       │     Acknowledgment                          │                   │
│       │◄────────────────────────────────────────────│                   │
│       │                                             │                   │
│       │                                             │ ◄─ Resource       │
│       │                                             │    Changes        │
│       │                                             │                   │
│       │     Notification (new data)                 │                   │
│       │◄────────────────────────────────────────────│                   │
│       │                                             │                   │
│       │                                             │ ◄─ Resource       │
│       │                                             │    Changes        │
│       │                                             │                   │
│       │     Notification (new data)                 │                   │
│       │◄────────────────────────────────────────────│                   │
│       │                                             │                   │
│       │     Unsubscribe(resource_uri)               │                   │
│       │────────────────────────────────────────────►│                   │
│       │                                             │                   │
│                                                                         │
│   Use Cases:                                                           │
│   • Game state updates                                                 │
│   • Score changes                                                      │
│   • League standings                                                   │
│   • Log monitoring                                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SECURITY LAYERS                                    │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │                    SANDBOX ENVIRONMENT                          │  │
│   │                       (Docker Container)                        │  │
│   │                                                                 │  │
│   │   ┌─────────────────────────────────────────────────────────┐  │  │
│   │   │                 ISOLATED EXECUTION                      │  │  │
│   │   │                                                         │  │  │
│   │   │  ┌───────────────────────────────────────────────────┐ │  │  │
│   │   │  │              LIMITED FILE ACCESS                  │ │  │  │
│   │   │  │                                                   │ │  │  │
│   │   │  │   ✓ /app/data     (allowed)                      │ │  │  │
│   │   │  │   ✓ /app/logs     (allowed)                      │ │  │  │
│   │   │  │   ✗ /etc          (blocked)                      │ │  │  │
│   │   │  │   ✗ /home         (blocked)                      │ │  │  │
│   │   │  │   ✗ /root         (blocked)                      │ │  │  │
│   │   │  └───────────────────────────────────────────────────┘ │  │  │
│   │   │                                                         │  │  │
│   │   │  ┌───────────────────────────────────────────────────┐ │  │  │
│   │   │  │              INPUT VALIDATION                     │ │  │  │
│   │   │  │                                                   │ │  │  │
│   │   │  │   • Sanitize all user inputs                     │ │  │  │
│   │   │  │   • Validate at system boundaries                │ │  │  │
│   │   │  │   • Reject suspicious patterns                   │ │  │  │
│   │   │  └───────────────────────────────────────────────────┘ │  │  │
│   │   │                                                         │  │  │
│   │   │  ┌───────────────────────────────────────────────────┐ │  │  │
│   │   │  │           HUMAN-IN-THE-LOOP                       │ │  │  │
│   │   │  │                                                   │ │  │  │
│   │   │  │   • Approval for sensitive operations            │ │  │  │
│   │   │  │   • Audit log for all actions                    │ │  │  │
│   │   │  │   • Rate limiting                                │ │  │  │
│   │   │  └───────────────────────────────────────────────────┘ │  │  │
│   │   └─────────────────────────────────────────────────────────┘  │  │
│   └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│   ⚠️  WARNING: Prompt Injection Risk                                   │
│   - Malicious instructions hidden in data sources                      │
│   - Always validate external content                                   │
│   - Never blindly execute LLM suggestions                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Progress Tracking

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PROGRESS TRACKING FLOW                               │
│                                                                         │
│   ┌────────┐                                    ┌────────┐             │
│   │ Client │                                    │ Server │             │
│   └───┬────┘                                    └───┬────┘             │
│       │                                             │                   │
│       │  Tool Call + Progress Token                 │                   │
│       │  { token: "abc123", tool: "search" }        │                   │
│       │────────────────────────────────────────────►│                   │
│       │                                             │                   │
│       │                                             │  Start long       │
│       │                                             │  operation        │
│       │                                             │                   │
│       │  Progress Update (10%)                      │                   │
│       │◄────────────────────────────────────────────│                   │
│       │  { token: "abc123", progress: 10 }          │                   │
│       │                                             │                   │
│       │  Progress Update (50%)                      │                   │
│       │◄────────────────────────────────────────────│                   │
│       │  { token: "abc123", progress: 50 }          │                   │
│       │                                             │                   │
│       │  Progress Update (90%)                      │                   │
│       │◄────────────────────────────────────────────│                   │
│       │  { token: "abc123", progress: 90 }          │                   │
│       │                                             │                   │
│       │  Final Result (100%)                        │                   │
│       │◄────────────────────────────────────────────│                   │
│       │  { token: "abc123", result: {...} }         │                   │
│                                                                         │
│   Benefits:                                                            │
│   • User knows system is working                                       │
│   • Can estimate completion time                                       │
│   • Client can cancel if needed                                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### Project Module Structure

```
src/
├── client/                     # MCP Client Implementation
│   ├── mcp_client.py           # Main client orchestrating all components
│   ├── session_manager.py      # Active session tracking
│   ├── tool_registry.py        # Tool discovery with namespace management
│   ├── connection_manager.py   # Heartbeat, retry, circuit breaker
│   ├── message_queue.py        # Priority-based message handling
│   └── resource_manager.py     # Resource caching & subscriptions
│
├── server/                     # MCP Server Implementation
│   ├── mcp_server.py           # Full MCP server with tools/resources
│   ├── base_server.py          # Base HTTP server utilities
│   ├── tools/                  # Tool implementations
│   └── resources/              # Resource providers
│
├── transport/                  # Transport Layer
│   ├── base.py                 # Abstract transport interface
│   ├── json_rpc.py             # JSON-RPC 2.0 message handling
│   └── http_transport.py       # HTTP POST transport
│
├── game/                       # Game Logic (Separation of Concerns)
│   ├── odd_even.py             # Odd/Even game rules
│   └── match.py                # Match scheduling & management
│
├── agents/                     # AI Agent Implementations
│   ├── league_manager.py       # League orchestration agent
│   ├── referee.py              # Game referee agent
│   └── player.py               # Player agent with strategies
│
├── common/                     # Shared Utilities
│   ├── config.py               # Configuration management
│   ├── logger.py               # Structured logging
│   ├── exceptions.py           # Custom exceptions
│   └── protocol.py             # Protocol message schemas
│
└── main.py                     # Main entry point & CLI
```

### Key Implementation Patterns

#### 1. Async/Await Pattern

All I/O operations use Python's `asyncio` for non-blocking execution:

```python
async def handle_request(self, request: dict) -> dict:
    # Non-blocking network I/O
    response = await self.transport.send(request)
    return response
```

#### 2. Circuit Breaker Implementation

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    async def call(self, func: Callable) -> Any:
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitOpenError("Circuit is open")

        try:
            result = await func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
```

#### 3. Exponential Backoff with Jitter

```python
def calculate_delay(attempt: int, base: float = 1.0, max_delay: float = 30.0) -> float:
    delay = min(base * (2 ** attempt), max_delay)
    jitter = random.uniform(0, delay * 0.1)
    return delay + jitter
```

#### 4. Namespace Collision Prevention

```python
class ToolRegistry:
    def register_tool(self, server_name: str, tool: Tool) -> None:
        # Namespaced tool name: server_name.tool_name
        namespaced_name = f"{server_name}.{tool.name}"
        self.tools[namespaced_name] = tool
```

### Configuration Schema

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
  },
  "game": {
    "type": "even_odd",
    "rounds_to_win": 3,
    "max_rounds": 5,
    "move_timeout_seconds": 30
  },
  "retry": {
    "max_attempts": 3,
    "base_delay": 1.0,
    "max_delay": 30.0
  },
  "circuit_breaker": {
    "failure_threshold": 5,
    "recovery_timeout": 30.0
  }
}
```

### Scalability Design (100K+ Players)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SCALABLE ARCHITECTURE                              │
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                      LOAD BALANCER                                │    │
│   │                    (Round-Robin / Least Connections)               │    │
│   └───────────────────────────────┬───────────────────────────────────┘    │
│                                   │                                         │
│   ┌───────────────────────────────┼───────────────────────────────────┐    │
│   │                               │                                   │    │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │    │
│   │  │  League     │  │  League     │  │  League     │               │    │
│   │  │  Manager 1  │  │  Manager 2  │  │  Manager N  │               │    │
│   │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │    │
│   │         │                │                │                       │    │
│   │         └────────────────┼────────────────┘                       │    │
│   │                          │                                        │    │
│   │                   ┌──────┴──────┐                                 │    │
│   │                   │   Message   │                                 │    │
│   │                   │    Queue    │                                 │    │
│   │                   │  (Redis)    │                                 │    │
│   │                   └──────┬──────┘                                 │    │
│   │                          │                                        │    │
│   │         ┌────────────────┼────────────────┐                       │    │
│   │         │                │                │                       │    │
│   │  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐               │    │
│   │  │  Referee    │  │  Referee    │  │  Referee    │               │    │
│   │  │  Pool 1     │  │  Pool 2     │  │  Pool N     │               │    │
│   │  └─────────────┘  └─────────────┘  └─────────────┘               │    │
│   │                                                                   │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                         SHARED STATE                              │    │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │    │
│   │  │   Redis     │  │  PostgreSQL │  │  S3/Object  │               │    │
│   │  │   Cache     │  │   Database  │  │   Storage   │               │    │
│   │  └─────────────┘  └─────────────┘  └─────────────┘               │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Player Agent Decision Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PLAYER AGENT DECISION FLOW                            │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                           SENSORS                                   │  │
│   │                                                                     │  │
│   │   Receive Game State:                                               │  │
│   │   • Your role (ODD/EVEN)                                            │  │
│   │   • Current scores                                                  │  │
│   │   • Previous round results                                          │  │
│   │   • Opponent's pattern history                                      │  │
│   │                                                                     │  │
│   └─────────────────────────────────┬───────────────────────────────────┘  │
│                                     │                                       │
│                                     ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      DECISION MODEL (LLM)                           │  │
│   │                                                                     │  │
│   │   Strategy Options:                                                 │  │
│   │   1. Random Strategy - Pure random selection                        │  │
│   │   2. Pattern Analysis - Detect opponent patterns                    │  │
│   │   3. Counter Strategy - Counter predicted opponent move             │  │
│   │   4. LLM Strategy - Use AI for decision making                      │  │
│   │                                                                     │  │
│   │   ┌─────────────────────────────────────────────────────────────┐  │  │
│   │   │                    LLM PROMPT                               │  │  │
│   │   │                                                             │  │  │
│   │   │   "You are playing Odd/Even. Your role is {role}.           │  │  │
│   │   │    Current score: You {your_score} - Opponent {opp_score}   │  │  │
│   │   │    History: {previous_rounds}                               │  │  │
│   │   │    Choose a number 1-5 that maximizes your chance."         │  │  │
│   │   └─────────────────────────────────────────────────────────────┘  │  │
│   │                                                                     │  │
│   └─────────────────────────────────┬───────────────────────────────────┘  │
│                                     │                                       │
│                                     ▼                                       │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                          ACTUATORS                                  │  │
│   │                                                                     │  │
│   │   Send Move Response:                                               │  │
│   │   {                                                                 │  │
│   │     "protocol": "league.v1",                                        │  │
│   │     "message_type": "MOVE_RESPONSE",                                │  │
│   │     "move": { "number": 3 }                                         │  │
│   │   }                                                                 │  │
│   │                                                                     │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## References

- [Model Context Protocol Specification](https://spec.modelcontextprotocol.io/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [Assignment Requirements](../REQUIREMENTS.md)
- [API Documentation](./API.md)

---

*Last Updated: December 2024*

