# API Documentation

## Overview

This document describes the API endpoints and message formats for the MCP Multi-Agent Game League system.

---

## Transport Layer

All communication uses **HTTP POST** to `/mcp` endpoint with **JSON-RPC 2.0** format.

### Base URLs

| Component | URL |
|-----------|-----|
| League Manager | `http://localhost:8000/mcp` |
| Referee | `http://localhost:8001/mcp` |
| Player N | `http://localhost:81XX/mcp` |

---

## JSON-RPC 2.0 Format

### Request Format

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {}
  }
}
```

### Response Format

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "result": {}
}
```

### Error Response Format

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "error": {
    "code": -32600,
    "message": "Invalid Request",
    "data": {}
  }
}
```

### Standard Error Codes

| Code | Message | Description |
|------|---------|-------------|
| -32700 | Parse error | Invalid JSON |
| -32600 | Invalid Request | Not a valid Request object |
| -32601 | Method not found | Method does not exist |
| -32602 | Invalid params | Invalid method parameters |
| -32603 | Internal error | Internal JSON-RPC error |

---

## MCP Methods

### Initialize

Establish connection with server.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {},
      "resources": {}
    },
    "clientInfo": {
      "name": "player-agent",
      "version": "1.0.0"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {},
      "resources": {}
    },
    "serverInfo": {
      "name": "league-manager",
      "version": "1.0.0"
    }
  }
}
```

### List Tools

Get available tools from server.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "register_player",
        "description": "Register a new player to the league",
        "inputSchema": {
          "type": "object",
          "properties": {
            "player_name": {"type": "string"},
            "endpoint": {"type": "string"}
          },
          "required": ["player_name", "endpoint"]
        }
      }
    ]
  }
}
```

### Call Tool

Execute a tool on the server.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "register_player",
    "arguments": {
      "player_name": "AlphaBot",
      "endpoint": "http://localhost:8101/mcp"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"status\": \"ACCEPTED\", \"player_id\": \"P01\"}"
      }
    ]
  }
}
```

### List Resources

Get available resources from server.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "resources/list",
  "params": {}
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "resources": [
      {
        "uri": "league://standings",
        "name": "League Standings",
        "description": "Current league standings",
        "mimeType": "application/json"
      }
    ]
  }
}
```

### Read Resource

Read a specific resource.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "resources/read",
  "params": {
    "uri": "league://standings"
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "contents": [
      {
        "uri": "league://standings",
        "mimeType": "application/json",
        "text": "{\"standings\": [...]}"
      }
    ]
  }
}
```

---

## League Protocol Messages

### Protocol Version

All league messages MUST include:
```json
"protocol": "league.v1"
```

### Player Registration

#### LEAGUE_REGISTER_REQUEST

**Direction:** Player → League Manager

```json
{
  "protocol": "league.v1",
  "message_type": "LEAGUE_REGISTER_REQUEST",
  "league_id": "league_2024_01",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "sender": "player:new_player",
  "timestamp": "2024-12-13T10:00:00Z",
  "player_meta": {
    "display_name": "Agent Alpha",
    "version": "1.0.0",
    "game_types": ["even_odd"],
    "contact_endpoint": "http://localhost:8101/mcp"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `protocol` | string | ✅ | Must be "league.v1" |
| `message_type` | string | ✅ | "LEAGUE_REGISTER_REQUEST" |
| `league_id` | string | ✅ | Target league ID |
| `conversation_id` | string | ✅ | UUID for tracking |
| `sender` | string | ✅ | "player:{id}" format |
| `timestamp` | string | ✅ | ISO-8601 format |
| `player_meta.display_name` | string | ✅ | Human-readable name |
| `player_meta.version` | string | ✅ | Agent version |
| `player_meta.game_types` | array | ✅ | Must include "even_odd" |
| `player_meta.contact_endpoint` | string | ✅ | MCP endpoint URL |

#### LEAGUE_REGISTER_RESPONSE

**Direction:** League Manager → Player

```json
{
  "protocol": "league.v1",
  "message_type": "LEAGUE_REGISTER_RESPONSE",
  "league_id": "league_2024_01",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "sender": "league_manager",
  "timestamp": "2024-12-13T10:00:01Z",
  "status": "ACCEPTED",
  "player_id": "P01",
  "reason": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | "ACCEPTED" or "REJECTED" |
| `player_id` | string | Assigned player ID (e.g., "P01") |
| `reason` | string | Only provided if rejected |

---

### Game Messages

#### GAME_START

**Direction:** Referee → Players

```json
{
  "protocol": "league.v1",
  "message_type": "GAME_START",
  "league_id": "league_2024_01",
  "round_id": 1,
  "match_id": "R1M1",
  "conversation_id": "uuid",
  "sender": "referee",
  "timestamp": "2024-12-13T10:05:00Z",
  "game_config": {
    "game_type": "even_odd",
    "rounds_to_win": 3,
    "max_rounds": 5,
    "time_limit_seconds": 30
  },
  "players": [
    {"player_id": "P01", "role": "ODD"},
    {"player_id": "P02", "role": "EVEN"}
  ]
}
```

#### MOVE_REQUEST

**Direction:** Referee → Player

```json
{
  "protocol": "league.v1",
  "message_type": "MOVE_REQUEST",
  "league_id": "league_2024_01",
  "round_id": 1,
  "match_id": "R1M1",
  "conversation_id": "uuid",
  "sender": "referee",
  "timestamp": "2024-12-13T10:05:01Z",
  "game_round": 1,
  "game_state": {
    "your_role": "ODD",
    "scores": {"P01": 0, "P02": 0},
    "previous_rounds": []
  },
  "time_limit_seconds": 30
}
```

#### MOVE_RESPONSE

**Direction:** Player → Referee

```json
{
  "protocol": "league.v1",
  "message_type": "MOVE_RESPONSE",
  "league_id": "league_2024_01",
  "round_id": 1,
  "match_id": "R1M1",
  "conversation_id": "uuid",
  "sender": "player:P01",
  "timestamp": "2024-12-13T10:05:05Z",
  "game_round": 1,
  "move": {
    "number": 3
  }
}
```

| Field | Type | Constraints |
|-------|------|-------------|
| `move.number` | integer | 1-5 inclusive |

#### ROUND_RESULT

**Direction:** Referee → Players

```json
{
  "protocol": "league.v1",
  "message_type": "ROUND_RESULT",
  "league_id": "league_2024_01",
  "round_id": 1,
  "match_id": "R1M1",
  "conversation_id": "uuid",
  "sender": "referee",
  "timestamp": "2024-12-13T10:05:10Z",
  "game_round": 1,
  "moves": {
    "P01": 3,
    "P02": 2
  },
  "sum": 5,
  "sum_type": "ODD",
  "round_winner": "P01",
  "scores": {"P01": 1, "P02": 0}
}
```

#### GAME_END

**Direction:** Referee → Players

```json
{
  "protocol": "league.v1",
  "message_type": "GAME_END",
  "league_id": "league_2024_01",
  "round_id": 1,
  "match_id": "R1M1",
  "conversation_id": "uuid",
  "sender": "referee",
  "timestamp": "2024-12-13T10:10:00Z",
  "final_scores": {"P01": 3, "P02": 2},
  "winner": "P01",
  "match_points": {
    "P01": 3,
    "P02": 0
  }
}
```

---

## League Manager Tools

### register_player

Register a new player to the league.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "player_name": {"type": "string"},
    "endpoint": {"type": "string"},
    "version": {"type": "string"}
  },
  "required": ["player_name", "endpoint"]
}
```

### get_standings

Get current league standings.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "league_id": {"type": "string"}
  },
  "required": ["league_id"]
}
```

**Response:**
```json
{
  "standings": [
    {"rank": 1, "player_id": "P01", "points": 9, "wins": 3, "losses": 0},
    {"rank": 2, "player_id": "P02", "points": 6, "wins": 2, "losses": 1}
  ]
}
```

### schedule_match

Schedule a new match between two players.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "player1_id": {"type": "string"},
    "player2_id": {"type": "string"},
    "round_id": {"type": "integer"}
  },
  "required": ["player1_id", "player2_id", "round_id"]
}
```

---

## Referee Tools

### start_game

Start a game between two players.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "player1_id": {"type": "string"},
    "player2_id": {"type": "string"},
    "match_id": {"type": "string"}
  },
  "required": ["player1_id", "player2_id", "match_id"]
}
```

### validate_move

Validate a player's move.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "player_id": {"type": "string"},
    "move": {"type": "integer", "minimum": 1, "maximum": 5}
  },
  "required": ["player_id", "move"]
}
```

### get_game_state

Get current game state.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "match_id": {"type": "string"}
  },
  "required": ["match_id"]
}
```

---

## Player Tools

### make_move

Make a move in the current game.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "number": {"type": "integer", "minimum": 1, "maximum": 5}
  },
  "required": ["number"]
}
```

### get_my_state

Get player's current state and game info.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {}
}
```

---

## Error Handling

### Protocol Errors

| Error | Description | Action |
|-------|-------------|--------|
| Invalid protocol version | Protocol not "league.v1" | Reject message |
| Missing required field | Required field not present | Return error |
| Invalid move | Number not in 1-5 range | Reject move |
| Timeout | Response not received in time | Default loss |

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request (invalid JSON) |
| 404 | Method not found |
| 500 | Internal Server Error |

---

## Rate Limiting

| Component | Limit |
|-----------|-------|
| League Manager | 100 requests/minute |
| Referee | 50 requests/minute per game |
| Player | 10 moves/minute during game |

---

## Subscription Resources

### league://standings

Real-time league standings updates.

### league://schedule

Current and upcoming match schedule.

### game://state/{match_id}

Real-time game state for a specific match.

---

*Last Updated: December 2024*

