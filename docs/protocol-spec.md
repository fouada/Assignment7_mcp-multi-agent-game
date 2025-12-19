# MCP Multi-Agent Game Protocol Specification

**Version:** 2.0 (league.v2)  
**Status:** Reference Implementation

## Overview

This document specifies the Model Context Protocol (MCP) based communication protocol for the Even/Odd League system.

## Protocol Version

```
protocol: "league.v2"
```

## Agent Types

| Agent Type | Role | Port Range |
|------------|------|------------|
| League Manager | Orchestrates league | 8000 |
| Referee | Manages games | 8001-8099 |
| Player | Participates in games | 8100-8199 |

## Message Envelope

All messages follow this structure:

```json
{
  "protocol": "league.v2",
  "message_id": "uuid-v4",
  "type": "MESSAGE_TYPE",
  "sender": "agent_type:agent_id",
  "timestamp": "2025-01-01T00:00:00.000Z",
  "payload": { ... },
  "auth_token": "optional_token"
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| protocol | string | Must be "league.v2" |
| message_id | string | UUID v4 |
| type | string | Message type enum |
| sender | string | Format: `agent_type:agent_id` |
| timestamp | string | ISO 8601 UTC |
| payload | object | Message-specific data |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| auth_token | string | Authentication token |
| correlation_id | string | Links related messages |

## Message Types

### Registration Messages

- `REFEREE_REGISTER_REQUEST` - Referee registers with league
- `REFEREE_REGISTER_RESPONSE` - League confirms referee registration
- `PLAYER_REGISTER_REQUEST` - Player registers with league
- `PLAYER_REGISTER_RESPONSE` - League confirms player registration

### Round Messages

- `ROUND_ANNOUNCEMENT` - League announces new round
- `ROUND_START` - Signal to begin round
- `ROUND_END` - Signal that round has ended
- `ROUND_RESULT` - Round result details

### Game Messages

- `GAME_INVITE` - Referee invites player to game
- `GAME_INVITE_RESPONSE` - Player responds to invitation
- `GAME_START` - Game begins
- `MOVE_REQUEST` - Referee requests player's move
- `MOVE_RESPONSE` - Player submits move
- `GAME_RESULT` - Game outcome

### League Messages

- `LEAGUE_STANDINGS_UPDATE` - Updated standings after round
- `MATCH_RESULT` - Match result report

### Error Messages

- `LEAGUE_ERROR` - League-level error
- `GAME_ERROR` - Game-level error

## Agent Lifecycle

### States

| State | Description |
|-------|-------------|
| INIT | Agent started, not yet registered |
| REGISTERED | Successfully registered, has auth_token |
| ACTIVE | Participating in games |
| SUSPENDED | Temporarily suspended (timeout) |
| SHUTDOWN | Agent finished activity |

### State Transitions

```
INIT ──[register_success]──► REGISTERED
INIT ──[error]──────────────► SHUTDOWN
REGISTERED ──[league_start]──► ACTIVE
REGISTERED ──[league_end]────► SHUTDOWN
ACTIVE ──[timeout]───────────► SUSPENDED
SUSPENDED ──[recover]────────► ACTIVE
SUSPENDED ──[max_fails]──────► SHUTDOWN
```

## Game States

The Even/Odd game progresses through these states:

| State | Description |
|-------|-------------|
| WAITING_FOR_PLAYERS | Waiting for player acceptance |
| COLLECTING_CHOICES | Collecting player number choices (1-5) |
| DRAWING_NUMBER | System draws random number |
| FINISHED | Game complete |

## Timeouts

| Operation | Timeout (seconds) |
|-----------|-------------------|
| referee_register | 10 |
| league_register | 10 |
| game_join_ack | 5 |
| choose_parity | 30 |
| game_over | 5 |
| match_result_report | 10 |
| default | 10 |

## Error Codes

### League Errors

| Code | Name | Description |
|------|------|-------------|
| L001 | REGISTRATION_FAILED | Registration failed |
| L002 | LEAGUE_FULL | Maximum players reached |
| L003 | ALREADY_REGISTERED | Agent already registered |
| L004 | NOT_REGISTERED | Agent not registered |
| L005 | INVALID_LEAGUE | League not found |

### Game Errors

| Code | Name | Description |
|------|------|-------------|
| G001 | INVALID_MOVE | Invalid move submitted |
| G002 | TIMEOUT | Player timeout |
| G003 | GAME_NOT_FOUND | Game does not exist |
| G004 | NOT_YOUR_TURN | Move submitted out of turn |
| G005 | GAME_ALREADY_STARTED | Cannot join started game |

## Scoring

### Per Match

| Outcome | Points |
|---------|--------|
| Win | 3 |
| Draw | 1 |
| Loss | 0 |

### League Standings

Standings are sorted by:
1. Points (descending)
2. Wins (descending)
3. Draws (descending)
4. Player ID (ascending - tiebreaker)

## References

1. [Model Context Protocol](https://modelcontextprotocol.io/)
2. [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)

