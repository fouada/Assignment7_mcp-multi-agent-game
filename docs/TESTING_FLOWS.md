# 🧪 Testing Flows & Expected Results

> **Complete Guide to Testing the MCP Multi-Agent Game League**
>
> This document describes all testing flows, how to execute them, and what results to expect.

---

## 📋 Table of Contents

1. [Quick Test Summary](#-quick-test-summary)
2. [Unit Tests](#-unit-tests)
3. [Integration Tests - Full League](#-integration-tests---full-league)
4. [Manual Component Testing](#-manual-component-testing)
5. [Message Flow Testing](#-message-flow-testing)
6. [Strategy Testing](#-strategy-testing)
7. [Error Handling Tests](#-error-handling-tests)
8. [Troubleshooting](#-troubleshooting)

---

## 🚀 Quick Test Summary

| Test Type | Command | Duration | Purpose |
|-----------|---------|----------|---------|
| **Unit Tests** | `uv run pytest tests/ -v` | ~10 seconds | Verify core components |
| **Full League** | `uv run python -m src.main --run` | ~30 seconds | End-to-end integration |
| **Debug Mode** | `uv run python -m src.main --run --debug` | ~30 seconds | Detailed logging |
| **With Coverage** | `uv run pytest tests/ --cov=src` | ~15 seconds | Test coverage report |
| **Random Strategy** | `uv run python -m src.main --run --strategy random` | ~30 seconds | Test random moves |
| **Pattern Strategy** | `uv run python -m src.main --run --strategy pattern` | ~30 seconds | Test pattern counter |
| **LLM Strategy** | `uv run python -m src.main --run --strategy llm` | ~60 seconds | Test AI decisions |

---

## 🧪 Unit Tests

### Running All Unit Tests

```bash
# Navigate to project root
cd /path/to/Assignment_7_MCP_Multi_Agent_Game

# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_game.py -v
uv run pytest tests/test_protocol.py -v
uv run pytest tests/test_transport.py -v
```

### Expected Output - All Tests Passing

```
========================= test session starts ==========================
platform darwin -- Python 3.11.x, pytest-7.x.x
collected 85 items

tests/test_config_loader.py::TestConfigLoader::test_load_system PASSED
tests/test_config_loader.py::TestConfigLoader::test_load_league PASSED
tests/test_config_loader.py::TestConfigLoader::test_load_games_registry PASSED
...
tests/test_game.py::TestOddEvenRules::test_validate_valid_move PASSED
tests/test_game.py::TestOddEvenRules::test_calculate_result_odd_wins PASSED
tests/test_game.py::TestOddEvenGame::test_game_creation PASSED
tests/test_game.py::TestMatchScheduler::test_round_robin_4_players PASSED
...
tests/test_protocol.py::TestProtocol::test_protocol_version PASSED
tests/test_protocol.py::TestMessageFactory::test_register_request PASSED
tests/test_protocol.py::TestMessageFactory::test_game_invite PASSED
...
tests/test_transport.py::TestJsonRpcRequest::test_create_request PASSED
tests/test_transport.py::TestJsonRpcResponse::test_create_success_response PASSED
...
tests/test_lifecycle.py::TestAgentLifecycleManager::test_initial_state PASSED
tests/test_lifecycle.py::TestAgentLifecycleManager::test_full_lifecycle PASSED
...
tests/test_repositories.py::TestStandingsRepository::test_save_and_load_standings PASSED
tests/test_repositories.py::TestMatchRepository::test_record_result PASSED
...
tests/test_logger.py::TestJSONLWriter::test_log_league_event PASSED
tests/test_logger.py::TestLeagueEventLogger::test_player_registered PASSED

========================= 85 passed in 8.52s ===========================
```

### Test Modules Description

| Module | Tests | Description |
|--------|-------|-------------|
| `test_game.py` | 23 tests | Game logic, rules, match scheduling |
| `test_protocol.py` | 25 tests | Message creation, validation |
| `test_transport.py` | 12 tests | JSON-RPC request/response handling |
| `test_lifecycle.py` | 15 tests | Agent state transitions |
| `test_repositories.py` | 12 tests | Data persistence |
| `test_config_loader.py` | 10 tests | Configuration loading |
| `test_logger.py` | 10 tests | Logging system |

---

## 🏆 Integration Tests - Full League

### Flow 1: Basic League (4 Players, Random/Pattern Strategies)

**Command:**
```bash
uv run python -m src.main --run
```

**What Happens:**
1. League Manager starts on port 8000
2. 2 Referees start on ports 8001, 8002
3. 4 Players start on ports 8101-8104
4. All agents register with League Manager
5. Round-robin tournament runs (3 rounds, 6 total matches)
6. Final standings displayed

**Expected Output:**

```
============================================================
Starting MCP Game League
============================================================
  League Manager: 1
  Referees: 2
  Players: 4
  Strategy: mixed
============================================================
INFO:     League Manager started at http://localhost:8000/mcp
INFO:     Referee REF01 started at http://localhost:8001/mcp
INFO:     Referee REF02 started at http://localhost:8002/mcp
INFO:     Referee REF01 registered with league manager
INFO:     Referee REF02 registered with league manager
INFO:     Player Player_1 started at http://localhost:8101/mcp
INFO:     Player Player_2 started at http://localhost:8102/mcp
INFO:     Player Player_3 started at http://localhost:8103/mcp
INFO:     Player Player_4 started at http://localhost:8104/mcp
INFO:     League started with 4 players
INFO:     League competition started!

==================================================
Starting Round 1/3
==================================================

INFO:     Match R1M1: P01 vs P04 (Referee: REF01)
INFO:     Match R1M2: P02 vs P03 (Referee: REF02)

Current Standings:
  1. Player_1: 3 pts
  2. Player_3: 3 pts
  3. Player_2: 0 pts
  4. Player_4: 0 pts

==================================================
Starting Round 2/3
==================================================

INFO:     Match R2M1: P01 vs P03 (Referee: REF01)
INFO:     Match R2M2: P04 vs P02 (Referee: REF02)

Current Standings:
  1. Player_1: 6 pts
  2. Player_3: 3 pts
  3. Player_4: 3 pts
  4. Player_2: 0 pts

==================================================
Starting Round 3/3
==================================================

INFO:     Match R3M1: P01 vs P02 (Referee: REF01)
INFO:     Match R3M2: P03 vs P04 (Referee: REF02)

==================================================
LEAGUE COMPLETE - Final Standings
==================================================
  1. Player_1: 9 pts (3W-0L)
  2. Player_3: 6 pts (2W-1L)
  3. Player_4: 3 pts (1W-2L)
  4. Player_2: 0 pts (0W-3L)

INFO:     League stopped
```

### Flow 2: Custom Configuration (6 Players, 3 Referees)

**Command:**
```bash
uv run python -m src.main --run --players 6 --referees 3
```

**Expected:**
- 1 League Manager
- 3 Referees on ports 8001, 8002, 8003
- 6 Players on ports 8101-8106
- 5 rounds (round-robin for 6 players)
- 15 total matches

### Flow 3: Debug Mode

**Command:**
```bash
uv run python -m src.main --run --debug
```

**Expected Additional Output:**
```
DEBUG:    Sending GAME_INVITE to P01
DEBUG:    Received GAME_JOIN_ACK from P01
DEBUG:    Player P01 chose number: 3
DEBUG:    Player P04 chose number: 7
DEBUG:    Round result: sum=10, even, winner=EVEN player
DEBUG:    Sending ROUND_RESULT to both players
DEBUG:    Match R1M1 completed: P04 wins
```

### Flow 4: LLM Strategy (Requires API Key)

**Command:**
```bash
# Set API key first
export ANTHROPIC_API_KEY=your_api_key_here

# Run with LLM strategy
uv run python -m src.main --run --strategy llm
```

**Expected:**
```
============================================================
Starting MCP Game League
============================================================
  League Manager: 1
  Referees: 2
  Players: 4
  Strategy: llm
  LLM: anthropic / claude-sonnet-4-20250514
============================================================
🧠 Using LLM strategy (Anthropic Claude) for all 4 players
...
```

---

## 🔧 Manual Component Testing

### Flow 5: Manual Multi-Terminal Setup

This flow lets you start each component in separate terminals for debugging.

**Terminal 1 - League Manager:**
```bash
uv run python -m src.main --component league --debug
```

**Expected Output:**
```
INFO:     League Manager started at http://localhost:8000/mcp
INFO:     Waiting for players to register...
```

**Terminal 2 - Referee 1:**
```bash
uv run python -m src.main --component referee --port 8001 --register
```

**Expected Output:**
```
INFO:     referee started at http://localhost:8001/mcp
INFO:     Registering with league manager...
INFO:     Referee registered successfully with token: ref_xxx
```

**Terminal 3 - Referee 2:**
```bash
uv run python -m src.main --component referee --name REF02 --port 8002 --register
```

**Terminal 4-7 - Players:**
```bash
# Terminal 4
uv run python -m src.main --component player --name "Alice" --port 8101 --register

# Terminal 5
uv run python -m src.main --component player --name "Bob" --port 8102 --register --strategy pattern

# Terminal 6
uv run python -m src.main --component player --name "Charlie" --port 8103 --register

# Terminal 7
uv run python -m src.main --component player --name "Diana" --port 8104 --register --strategy pattern
```

**Expected Output (per player):**
```
INFO:     player started at http://localhost:8101/mcp
INFO:     Registering with league manager...
INFO:     Player Alice registered successfully as P01 with token: tok_xxx
INFO:     Waiting for game invitations...
```

**Terminal 8 - Control Commands:**
```bash
# Start the league
uv run python -m src.main --start-league

# Run one round
uv run python -m src.main --run-round

# Check standings
uv run python -m src.main --get-standings

# Run all remaining rounds
uv run python -m src.main --run-all-rounds
```

**Expected Output (--get-standings):**
```json
{
  "standings": [
    {"rank": 1, "player_id": "P01", "display_name": "Alice", "points": 6, "wins": 2, "losses": 0},
    {"rank": 2, "player_id": "P03", "display_name": "Charlie", "points": 3, "wins": 1, "losses": 1},
    {"rank": 3, "player_id": "P02", "display_name": "Bob", "points": 3, "wins": 1, "losses": 1},
    {"rank": 4, "player_id": "P04", "display_name": "Diana", "points": 0, "wins": 0, "losses": 2}
  ]
}
```

---

## 📨 Message Flow Testing

### Testing Individual Message Types

You can verify specific message flows by examining the logs:

**Check logs directory:**
```bash
# League events
cat logs/league/league_2025_even_odd/events.log.jsonl | head -20

# Match events
cat logs/league/league_2025_even_odd/matches/R1M1.log.jsonl

# Agent events
cat logs/agents/P01.log.jsonl
```

**Expected Log Entry (PLAYER_REGISTERED):**
```json
{
  "timestamp": "2024-12-23T10:00:00.000Z",
  "league_id": "league_2025_even_odd",
  "event_type": "PLAYER_REGISTERED",
  "player_id": "P01",
  "display_name": "Player_1",
  "endpoint": "http://localhost:8101/mcp"
}
```

**Expected Log Entry (MOVE_SUBMITTED):**
```json
{
  "timestamp": "2024-12-23T10:01:00.000Z",
  "match_id": "R1M1",
  "event_type": "MOVE_SUBMITTED",
  "player_id": "P01",
  "round_number": 1,
  "move_value": 3
}
```

**Expected Log Entry (ROUND_RESULT):**
```json
{
  "timestamp": "2024-12-23T10:01:01.000Z",
  "match_id": "R1M1",
  "event_type": "ROUND_RESULT",
  "round_number": 1,
  "player_A_move": 3,
  "player_B_move": 7,
  "sum_value": 10,
  "is_odd": false,
  "winner_id": "P02"
}
```

---

## 🎯 Strategy Testing

The `--strategy` flag controls how players make move decisions. Available strategies:

| Strategy | Description | LLM Required | Move Range |
|----------|-------------|--------------|------------|
| `random` | Uniform random selection | ❌ No | 1-5 |
| `pattern` | Counter opponent patterns | ❌ No | 1-5 |
| `llm` | AI-powered (Claude/GPT) | ✅ Yes | 1-5 |
| `mixed` | Alternates random/pattern | ❌ No | 1-5 |

### Strategy Test 1: Random Strategy

**Command:**
```bash
uv run python -m src.main --run --strategy random --debug
```

**What to Verify:**
- All players use `RandomStrategy`
- Move values are uniformly distributed (1-5)
- No pattern analysis in logs

**Expected Debug Output:**
```
INFO:     Player Player_1 started at http://localhost:8101/mcp
DEBUG:    [Player_1] Strategy: RandomStrategy
DEBUG:    [Player_1] Round 1: chose move 3 (random)
DEBUG:    [Player_1] Round 2: chose move 1 (random)
DEBUG:    [Player_1] Round 3: chose move 5 (random)
```

**Verification:**
```bash
# Check strategy in logs
grep -i "strategy" logs/system/system.log.jsonl
# Should show: "strategy": "RandomStrategy" for all players
```

---

### Strategy Test 2: Pattern Strategy

**Command:**
```bash
uv run python -m src.main --run --strategy pattern --debug
```

**What to Verify:**
- All players use `PatternStrategy`
- Players analyze opponent history
- Moves adapt based on opponent's previous moves

**Expected Debug Output:**
```
INFO:     Player Player_1 started at http://localhost:8101/mcp
DEBUG:    [Player_1] Strategy: PatternStrategy
DEBUG:    [Player_1] Round 1: chose move 4 (no history, random start)
DEBUG:    [Player_1] Round 2: analyzing opponent moves [3]
DEBUG:    [Player_1] Round 2: opponent avg=3.0, predicted sum=6.0
DEBUG:    [Player_1] Round 2: chose move 2 (pattern counter)
```

**How Pattern Strategy Works:**
```
1. Round 1: Random (no history available)
2. Round 2+: Analyzes last 3 opponent moves
3. Calculates average opponent move
4. Predicts sum and chooses to flip parity if needed
5. ODD player: wants odd sum → chooses to make sum odd
6. EVEN player: wants even sum → chooses to make sum even
```

---

### Strategy Test 3: Mixed Strategy (Default)

**Command:**
```bash
uv run python -m src.main --run --strategy mixed --debug
# Or simply (mixed is default):
uv run python -m src.main --run --debug
```

**What to Verify:**
- Players alternate between RandomStrategy and PatternStrategy
- Player 1, 3: RandomStrategy
- Player 2, 4: PatternStrategy

**Expected Debug Output:**
```
============================================================
Starting MCP Game League
============================================================
  Strategy: mixed
============================================================
INFO:     Player Player_1 started - Strategy: RandomStrategy
INFO:     Player Player_2 started - Strategy: PatternStrategy
INFO:     Player Player_3 started - Strategy: RandomStrategy
INFO:     Player Player_4 started - Strategy: PatternStrategy
```

**Verification:**
```bash
# Verify mixed assignment
uv run python -c "
strategies = ['random', 'pattern', 'random', 'pattern']
for i, s in enumerate(strategies):
    print(f'Player_{i+1}: {s}')
"
```

---

### Strategy Test 4: LLM Strategy (Claude/OpenAI)

**Prerequisites:**
```bash
# For Anthropic Claude (default)
export ANTHROPIC_API_KEY=sk-ant-xxxxx

# OR for OpenAI
export OPENAI_API_KEY=sk-xxxxx
```

**Command (Anthropic Claude):**
```bash
uv run python -m src.main --run --strategy llm --debug
```

**Command (OpenAI GPT-4):**
```bash
uv run python -m src.main --run --strategy llm --llm-provider openai --debug
```

**Command (Custom Model):**
```bash
uv run python -m src.main --run --strategy llm --llm-provider anthropic --llm-model claude-3-haiku-20240307
```

**What to Verify:**
- All players use `LLMStrategy`
- LLM API is called for each move
- Moves are based on game context and history
- Fallback to random if API fails

**Expected Debug Output:**
```
============================================================
Starting MCP Game League
============================================================
  Strategy: llm
  LLM: anthropic / claude-sonnet-4-20250514
============================================================
🧠 Using LLM strategy (Anthropic Claude) for all 4 players
INFO:     LLM Strategy initialized: anthropic / claude-sonnet-4-20250514
INFO:     Anthropic Claude client initialized
DEBUG:    [Player_1] Building LLM prompt for round 1
DEBUG:    [Player_1] Role: ODD, Score: 0-0, History: []
DEBUG:    [Player_1] Claude response: "3"
DEBUG:    [Player_1] LLM decided move: 3
```

**LLM Prompt Context Includes:**
- Game rules (Odd/Even)
- Player's assigned role (ODD or EVEN)
- Current scores
- Last 5 rounds of history
- Strategy hints (game theory, pattern recognition)

**Fallback Behavior:**
```
# If API key missing or API fails:
WARNING:  No API key for anthropic, falling back to random
DEBUG:    No LLM client, using random move
DEBUG:    LLM failed, using random fallback
```

---

### Strategy Test 5: Single Player with Specific Strategy

Start individual players with different strategies:

**Terminal 1 - League Manager:**
```bash
uv run python -m src.main --component league
```

**Terminal 2 - Random Player:**
```bash
uv run python -m src.main --component player --name "RandomBot" --port 8101 --strategy random --register
```

**Terminal 3 - Pattern Player:**
```bash
uv run python -m src.main --component player --name "PatternBot" --port 8102 --strategy pattern --register
```

**Terminal 4 - LLM Player:**
```bash
export ANTHROPIC_API_KEY=your_key
uv run python -m src.main --component player --name "ClaudeBot" --port 8103 --strategy llm --register
```

**Terminal 5 - Another Random Player:**
```bash
uv run python -m src.main --component player --name "RandomBot2" --port 8104 --strategy random --register
```

**Terminal 6 - Run League:**
```bash
uv run python -m src.main --start-league
uv run python -m src.main --run-all-rounds
```

---

### Strategy Verification Commands

**Check which strategy each player is using:**
```bash
# Query player status via MCP
curl -X POST http://localhost:8101/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"get_player_state","arguments":{}},"id":1}'
```

**Expected Response:**
```json
{
  "result": {
    "content": [{
      "text": "{\"player_id\": \"P01\", \"player_name\": \"RandomBot\", \"strategy\": \"RandomStrategy\", ...}"
    }]
  }
}
```

**Verify strategy in persisted data:**
```bash
# Check player config
cat data/players/P01/config.json | jq '.strategy'
```

---

### Strategy Comparison Test

Run multiple leagues with different strategies and compare results:

```bash
# Test 1: All Random
uv run python -m src.main --run --strategy random 2>&1 | tee /tmp/random_results.txt

# Test 2: All Pattern  
uv run python -m src.main --run --strategy pattern 2>&1 | tee /tmp/pattern_results.txt

# Test 3: Mixed
uv run python -m src.main --run --strategy mixed 2>&1 | tee /tmp/mixed_results.txt

# Test 4: LLM (if API key available)
uv run python -m src.main --run --strategy llm 2>&1 | tee /tmp/llm_results.txt

# Compare final standings
echo "=== Random ===" && grep -A4 "Final Standings" /tmp/random_results.txt
echo "=== Pattern ===" && grep -A4 "Final Standings" /tmp/pattern_results.txt
echo "=== Mixed ===" && grep -A4 "Final Standings" /tmp/mixed_results.txt
echo "=== LLM ===" && grep -A4 "Final Standings" /tmp/llm_results.txt
```

---

### Strategy Test Checklist

| Test | Command | Expected Result |
|------|---------|-----------------|
| ✅ Random works | `--strategy random` | Uniform 1-5 distribution |
| ✅ Pattern works | `--strategy pattern` | Adapts to opponent history |
| ✅ Mixed works | `--strategy mixed` | Alternating strategies |
| ✅ LLM works | `--strategy llm` | AI-powered decisions |
| ✅ LLM fallback | `--strategy llm` (no API key) | Falls back to random |
| ✅ OpenAI works | `--strategy llm --llm-provider openai` | GPT-4 decisions |
| ✅ Custom model | `--strategy llm --llm-model claude-3-haiku` | Uses specified model |
| ✅ Per-player strategy | `--component player --strategy X` | Individual assignment |

---

## ❌ Error Handling Tests

### Test 1: No League Manager Running

**Command:**
```bash
uv run python -m src.main --get-standings
```

**Expected Output:**
```
Error: Could not connect to league manager at http://localhost:8000/mcp
Make sure the league manager is running:
  uv run python -m src.main --component league
```

### Test 2: Player Registration Timeout

Start league manager but don't start players, then try to start league:

```bash
# Terminal 1
uv run python -m src.main --component league

# Terminal 2
uv run python -m src.main --start-league
```

**Expected Output:**
```json
{
  "success": false,
  "error": "Not enough players registered (0/2 minimum)"
}
```

### Test 3: Invalid Move Handling

The referee validates moves are in range 1-10. Invalid moves result in:
- Default move value (3) being used
- Error logged in match log file

---

## 📊 Data Verification

After running a league, verify data was persisted correctly:

### Check Standings
```bash
cat data/leagues/league_2025_even_odd/standings.json
```

**Expected:**
```json
{
  "league_id": "league_2025_even_odd",
  "round_id": 3,
  "standings": [
    {"rank": 1, "player_id": "P01", "display_name": "Player_1", "wins": 3, "losses": 0, "points": 9},
    {"rank": 2, "player_id": "P03", "display_name": "Player_3", "wins": 2, "losses": 1, "points": 6},
    {"rank": 3, "player_id": "P04", "display_name": "Player_4", "wins": 1, "losses": 2, "points": 3},
    {"rank": 4, "player_id": "P02", "display_name": "Player_2", "wins": 0, "losses": 3, "points": 0}
  ]
}
```

### Check Rounds
```bash
cat data/leagues/league_2025_even_odd/rounds.json
```

### Check Match Results
```bash
cat data/matches/league_2025_even_odd/R1M1.json
```

**Expected:**
```json
{
  "match_id": "R1M1",
  "league_id": "league_2025_even_odd",
  "round_id": 1,
  "player_A_id": "P01",
  "player_B_id": "P04",
  "winner_id": "P01",
  "player_A_score": 3,
  "player_B_score": 2,
  "status": "completed"
}
```

### Check Player History
```bash
cat data/players/P01/history.json
```

---

## 🔍 Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Dependencies not installed | Run `uv sync --all-extras` |
| `Connection refused` | Component not running | Start required component first |
| `Timeout error` | Slow network/LLM | Increase timeout in config |
| `Invalid API key` | Missing/wrong API key | Export correct `ANTHROPIC_API_KEY` |
| `Port already in use` | Previous process running | Kill process or use different port |

### Debug Tips

1. **Enable debug logging:**
   ```bash
   uv run python -m src.main --run --debug
   ```

2. **Check component health:**
   ```bash
   curl http://localhost:8000/mcp -X POST \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
   ```

3. **View real-time logs:**
   ```bash
   tail -f logs/system/system.log.jsonl
   ```

4. **Reset data:**
   ```bash
   rm -rf data/leagues/* data/matches/* data/players/*/history.json
   ```

---

## ✅ Test Checklist

Use this checklist to verify all flows work correctly:

- [ ] **Unit Tests**
  - [ ] `pytest tests/test_game.py -v` - All pass
  - [ ] `pytest tests/test_protocol.py -v` - All pass
  - [ ] `pytest tests/test_transport.py -v` - All pass
  - [ ] `pytest tests/test_lifecycle.py -v` - All pass
  - [ ] `pytest tests/test_repositories.py -v` - All pass
  - [ ] `pytest tests/test_config_loader.py -v` - All pass
  - [ ] `pytest tests/test_logger.py -v` - All pass

- [ ] **Integration Tests**
  - [ ] Full league with 4 players completes
  - [ ] All rounds execute correctly
  - [ ] Final standings are displayed
  - [ ] Data is persisted to files

- [ ] **Strategy Tests**
  - [ ] `--strategy random` - Uniform random 1-5 distribution
  - [ ] `--strategy pattern` - Adapts to opponent history
  - [ ] `--strategy mixed` - Alternating random/pattern
  - [ ] `--strategy llm` - AI-powered decisions (with API key)
  - [ ] LLM fallback to random when no API key
  - [ ] `--llm-provider openai` - OpenAI GPT works
  - [ ] `--llm-model X` - Custom model selection works
  - [ ] Per-player strategy via `--component player --strategy X`

- [ ] **Manual Tests**
  - [ ] Individual components start correctly
  - [ ] Registration with league works
  - [ ] Control commands work (--start-league, --get-standings)

- [ ] **Error Handling**
  - [ ] Connection errors are handled gracefully
  - [ ] Invalid moves use defaults
  - [ ] Timeout handling works

---

## 📈 Performance Benchmarks

| Operation | Expected Time |
|-----------|---------------|
| Unit test suite | < 15 seconds |
| Full 4-player league | < 30 seconds |
| Single match (5 rounds) | < 5 seconds |
| Player registration | < 1 second |
| Message round-trip | < 100ms |

---

<div align="center">

**Happy Testing! 🎮**

*Last Updated: December 24, 2024*

</div>

