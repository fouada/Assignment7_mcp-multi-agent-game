```markdown
# Operations Guide - Modular Component Architecture

## Table of Contents

1. [System Overview](#system-overview)
2. [Component-by-Component Operation](#component-by-component-operation)
3. [Complete Workflows](#complete-workflows)
4. [Testing and Verification](#testing-and-verification)
5. [Troubleshooting](#troubleshooting)
6. [Production Deployment](#production-deployment)

---

## System Overview

The MCP Multi-Agent Game League uses a **modular component architecture** where each component runs independently and communicates via:
- **Event Bus**: Real-time event distribution
- **Service Registry**: Dynamic component discovery
- **State Sync**: Guaranteed state synchronization
- **Dashboard**: Real-time WebSocket updates

### Architecture Diagram

```
┌────────────────────────────────────────────────────────────┐
│                  System Architecture                        │
└────────────────────────────────────────────────────────────┘

┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│  League Manager  │◄──────►│  Service Registry │◄──────►│    Dashboard     │
│   (Port 8000)    │        │   (Singleton)     │        │   (Port 8050)    │
└────────┬─────────┘        └─────────┬─────────┘        └────────┬─────────┘
         │                             │                           │
         │  ┌──────────────────────────┴──────────────┐           │
         │  │         Event Bus (Pub/Sub)             │           │
         │  │    - agent.registered                   │           │
         │  │    - tournament.round.started           │◄──────────┤
         │  │    - game.move.decision                 │           │
         │  │    - standings.updated                  │           │
         │  └─────────────────────────────────────────┘           │
         │                                                         │
    ┌────▼────┐         ┌───────┐         ┌──────────┐          │
    │ Referee │         │Referee│         │ Referee  │          │
    │  REF01  │         │ REF02 │         │  REF03   │          │
    │(Port    │         │(Port  │         │ (Port    │          │
    │ 8001)   │         │ 8002) │         │  8003)   │          │
    └────┬────┘         └───┬───┘         └────┬─────┘          │
         │                  │                   │                │
    ┌────▼────┐    ┌───────▼────┐    ┌────────▼──┐   ┌────────▼──┐
    │ Player  │    │   Player    │    │  Player   │   │  Player   │
    │ Alice   │    │     Bob     │    │  Charlie  │   │   Diana   │
    │(Port    │    │   (Port     │    │  (Port    │   │  (Port    │
    │ 8101)   │    │    8102)    │    │   8103)   │   │   8104)   │
    └─────────┘    └─────────────┘    └───────────┘   └───────────┘
```

---

## Component-by-Component Operation

### 1. League Manager + Dashboard

**Purpose**: Central tournament coordinator and real-time monitoring

**Startup**:
```bash
# Using shell script (recommended)
./launch_league.sh

# Using Python CLI
uv run python -m src.cli league --dashboard

# Without dashboard
uv run python -m src.cli league --no-dashboard

# Custom port
uv run python -m src.cli league --port 9000
```

**Endpoints**:
- League Manager API: `http://localhost:8000`
- Dashboard UI: `http://localhost:8050`

**Verification**:
```bash
# Check league manager health
curl http://localhost:8000/health

# Open dashboard
open http://localhost:8050
```

**What It Does**:
- Registers players and referees
- Schedules matches (round-robin)
- Tracks standings
- Publishes tournament events
- Streams state to dashboard

---

### 2. Referee Agent

**Purpose**: Manages individual matches between players

**Startup**:
```bash
# Using shell script (recommended)
./launch_referee.sh --id REF01 --port 8001

# Using Python CLI
uv run python -m src.cli referee --id REF01 --port 8001

# Without auto-registration
./launch_referee.sh --id REF01 --port 8001 --no-register

# Multiple referees (in separate terminals)
./launch_referee.sh --id REF01 --port 8001
./launch_referee.sh --id REF02 --port 8002
./launch_referee.sh --id REF03 --port 8003
```

**Options**:
- `--id ID`: Referee identifier (default: REF01)
- `--port PORT`: Port number (default: 8001)
- `--register`: Auto-register with league (default: true)
- `--no-register`: Don't auto-register
- `--debug`: Enable debug logging

**Verification**:
```bash
# Check referee health
curl http://localhost:8001/health

# Check registration
curl http://localhost:8000/api/referees
```

**What It Does**:
- Accepts match assignments from league manager
- Coordinates game rounds between two players
- Enforces game rules
- Reports match results to league manager

---

### 3. Player Agent

**Purpose**: Executes game strategy and makes moves

**Startup**:
```bash
# Using shell script (recommended)
./launch_player.sh --name Alice --port 8101 --strategy random

# Using Python CLI
uv run python -m src.cli player --name Alice --port 8101 --strategy random

# With LLM strategy
export ANTHROPIC_API_KEY=your-key
./launch_player.sh --name Bob --port 8102 --strategy llm

# With pattern strategy
./launch_player.sh --name Charlie --port 8103 --strategy pattern

# Without auto-registration
./launch_player.sh --name Diana --port 8104 --strategy random --no-register
```

**Options**:
- `--name NAME`: Player name (default: Player_1)
- `--port PORT`: Port number (default: 8101)
- `--strategy STRATEGY`: Strategy type (default: random)
  - `random`: Random moves
  - `pattern`: Alternating pattern
  - `llm`: AI-powered strategy (requires API key)
  - Custom plugin strategies
- `--register`: Auto-register with league (default: true)
- `--no-register`: Don't auto-register
- `--debug`: Enable debug logging

**Verification**:
```bash
# Check player health
curl http://localhost:8101/health

# Check registration
curl http://localhost:8000/api/players
```

**What It Does**:
- Registers with league manager
- Receives move requests from referees
- Executes strategy to decide moves
- Reports moves back to referees

---

## Complete Workflows

### Workflow 1: Quick Start (4 Players, 2 Referees)

**Terminal 1: League Manager**
```bash
./launch_league.sh
# Wait for "League Manager Running" message
```

**Terminal 2: Referee 1**
```bash
./launch_referee.sh --id REF01 --port 8001
# Wait for "Referee REF01 Running" message
```

**Terminal 3: Referee 2**
```bash
./launch_referee.sh --id REF02 --port 8002
# Wait for "Referee REF02 Running" message
```

**Terminal 4: Player Alice (Random)**
```bash
./launch_player.sh --name Alice --port 8101 --strategy random
# Wait for "Player Alice Running" message
```

**Terminal 5: Player Bob (Pattern)**
```bash
./launch_player.sh --name Bob --port 8102 --strategy pattern
# Wait for "Player Bob Running" message
```

**Terminal 6: Player Charlie (LLM)**
```bash
export ANTHROPIC_API_KEY=your-key
./launch_player.sh --name Charlie --port 8103 --strategy llm
# Wait for "Player Charlie Running" message
```

**Terminal 7: Player Diana (Random)**
```bash
./launch_player.sh --name Diana --port 8104 --strategy random
# Wait for "Player Diana Running" message
```

**Terminal 8: Control League**
```bash
# Start the league
uv run python -m src.main --start-league

# Run all rounds automatically
uv run python -m src.main --run-all-rounds

# Or run rounds one at a time
uv run python -m src.main --run-round
uv run python -m src.main --run-round
# ... etc

# Check standings
uv run python -m src.main --get-standings
```

**Browser: Monitor Dashboard**
```
Open: http://localhost:8050
```

### Workflow 2: Automated Startup

**Single Command**:
```bash
./example_modular_workflow.sh
```

This script:
1. Starts all components in background
2. Saves process IDs to `.component_pids`
3. Shows status of all components
4. Provides next steps

**Cleanup**:
```bash
./cleanup_components.sh
```

### Workflow 3: Incremental Component Addition

Start with minimal setup and add components dynamically:

```bash
# 1. Start core
./launch_league.sh
./launch_referee.sh --id REF01 --port 8001

# 2. Add players gradually
./launch_player.sh --name Alice --port 8101 --strategy random
# Wait, observe dashboard

./launch_player.sh --name Bob --port 8102 --strategy pattern
# Watch them register in dashboard

./launch_player.sh --name Charlie --port 8103 --strategy llm
./launch_player.sh --name Diana --port 8104 --strategy random

# 3. Start league when ready
uv run python -m src.main --start-league
uv run python -m src.main --run-all-rounds
```

### Workflow 4: Large Tournament (10 Players, 4 Referees)

```bash
# Terminal 1: League + Dashboard
./launch_league.sh

# Terminals 2-5: Referees
./launch_referee.sh --id REF01 --port 8001
./launch_referee.sh --id REF02 --port 8002
./launch_referee.sh --id REF03 --port 8003
./launch_referee.sh --id REF04 --port 8004

# Terminals 6-15: Players
for i in {1..10}; do
  port=$((8100 + i))
  strategy="random"
  [[ $((i % 3)) -eq 0 ]] && strategy="pattern"
  [[ $((i % 5)) -eq 0 ]] && strategy="llm"

  ./launch_player.sh --name "Player_$i" --port $port --strategy $strategy &
done

# Wait for registrations
sleep 5

# Start league
uv run python -m src.main --start-league
uv run python -m src.main --run-all-rounds
```

---

## Testing and Verification

### Unit Tests

```bash
# Run all launcher tests
pytest tests/launcher/ -v

# Run specific test file
pytest tests/launcher/test_component_launcher.py -v

# Run with coverage
pytest tests/launcher/ --cov=src/launcher --cov-report=html

# Run integration tests
pytest tests/launcher/test_integration_modular_flow.py -v -m integration
```

### Integration Tests

```bash
# Run full integration suite
pytest tests/launcher/test_integration_modular_flow.py -v

# Run performance tests
pytest tests/launcher/ -v -m slow

# Run all modular tests
pytest tests/launcher/ -v --cov=src/launcher
```

### Manual Verification Checklist

**League Manager**:
- [ ] Starts successfully on port 8000
- [ ] Dashboard accessible at port 8050
- [ ] Registers in service registry
- [ ] State sync service running

**Referee**:
- [ ] Starts successfully on specified port
- [ ] Auto-registers with league manager
- [ ] Appears in service registry
- [ ] Shows in dashboard referee list

**Player**:
- [ ] Starts successfully on specified port
- [ ] Auto-registers with league manager
- [ ] Appears in service registry
- [ ] Shows in dashboard player list
- [ ] Strategy correctly initialized

**State Synchronization**:
- [ ] Player registration updates dashboard immediately
- [ ] Round announcements appear in dashboard
- [ ] Match assignments visible in real-time
- [ ] Player moves shown live
- [ ] Standings update after each round

**Dashboard**:
- [ ] WebSocket connection established
- [ ] Player list populates
- [ ] Referee list populates
- [ ] Round counter updates
- [ ] Match list updates
- [ ] Standings table updates
- [ ] Real-time move animations (if supported)

---

## Troubleshooting

### Component Won't Start

**Symptoms**:
```
Error: Address already in use
```

**Solution**:
```bash
# Check what's using the port
lsof -i :8000

# Kill the process
kill <PID>

# Or use a different port
./launch_league.sh --port 9000
```

---

### Component Can't Register with League

**Symptoms**:
```
Failed to register with league manager
Connection refused
```

**Solution**:
```bash
# 1. Verify league manager is running
curl http://localhost:8000/health

# 2. Check league manager logs
tail -f logs/league.log

# 3. Verify network connectivity
ping localhost

# 4. Try manual registration
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"player_id": "test", "name": "Test Player"}'
```

---

### Dashboard Not Updating

**Symptoms**:
- Dashboard shows old data
- No real-time updates
- WebSocket not connected

**Solution**:
```bash
# 1. Check browser console for WebSocket errors
# Open browser DevTools (F12) and check console

# 2. Verify dashboard server running
curl http://localhost:8050/health

# 3. Check state sync service
# In Python console:
from src.launcher import get_state_sync
sync = get_state_sync()
print(sync._running)  # Should be True

# 4. Verify event bus
from src.common.events import get_event_bus
bus = get_event_bus()
print(bus.get_handler_count())  # Should be > 0

# 5. Restart dashboard
# Stop league manager and restart with --dashboard
```

---

### High Latency / Slow Updates

**Symptoms**:
- Dashboard updates delayed
- Matches take long time
- System feels sluggish

**Solution**:
```bash
# 1. Check system resources
top
# Look for high CPU/memory usage

# 2. Check event bus stats
# In Python:
from src.common.events import get_event_bus
bus = get_event_bus()
print(bus.get_stats())

# 3. Check state sync history size
from src.launcher import get_state_sync
sync = get_state_sync()
history = await sync.get_state_history()
print(len(history))  # If > 1000, consider clearing

# 4. Reduce number of components
# Use fewer players/referees for testing

# 5. Check network latency
ping localhost
```

---

### Memory Leak / Growing Memory Usage

**Symptoms**:
- Memory usage increases over time
- System becomes slow after running for a while

**Solution**:
```bash
# 1. Check event history size
# State sync keeps last 1000 events - this is bounded

# 2. Check for unclosed connections
lsof -p <PID> | wc -l

# 3. Monitor memory
ps aux | grep python

# 4. Restart components periodically
# For long-running tournaments, restart between rounds

# 5. Review logs for warnings
grep -i "warning\|error" logs/*.log
```

---

## Production Deployment

### Prerequisites

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone <repository>
cd mcp-multi-agent-game

# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### Deployment Options

#### Option 1: Systemd Services (Linux)

**Create service files**:

`/etc/systemd/system/mcp-league.service`:
```ini
[Unit]
Description=MCP League Manager
After=network.target

[Service]
Type=simple
User=mcp
WorkingDirectory=/opt/mcp-game
Environment="PATH=/home/mcp/.local/bin:/usr/bin"
ExecStart=/home/mcp/.local/bin/uv run python -m src.cli league --dashboard
Restart=always

[Install]
WantedBy=multi-user.target
```

**Start services**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-league
sudo systemctl start mcp-league
sudo systemctl status mcp-league
```

#### Option 2: Docker Compose

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  league:
    build: .
    command: uv run python -m src.cli league --dashboard
    ports:
      - "8000:8000"
      - "8050:8050"
    environment:
      - LEAGUE_ID=prod_league_01
    restart: unless-stopped

  referee_01:
    build: .
    command: uv run python -m src.cli referee --id REF01 --port 8001
    ports:
      - "8001:8001"
    depends_on:
      - league
    restart: unless-stopped

  referee_02:
    build: .
    command: uv run python -m src.cli referee --id REF02 --port 8002
    ports:
      - "8002:8002"
    depends_on:
      - league
    restart: unless-stopped
```

**Start**:
```bash
docker-compose up -d
docker-compose ps
docker-compose logs -f
```

#### Option 3: Kubernetes

See `k8s/` directory for Kubernetes manifests.

### Monitoring

**Health Checks**:
```bash
# League manager
curl http://localhost:8000/health

# Referees
curl http://localhost:8001/health
curl http://localhost:8002/health

# Players
curl http://localhost:8101/health
```

**Metrics** (if enabled):
```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Grafana dashboard
open http://localhost:3000
```

**Logging**:
```bash
# Centralized logs
tail -f logs/*.log

# Or with log aggregation (ELK, Splunk, etc.)
```

### Backup and Recovery

**State Snapshots**:
```python
from src.launcher import get_state_sync

sync = get_state_sync()
snapshot = await sync.create_snapshot("backup_2024_01_15")

# Snapshots are stored in memory
# Export to disk for persistence:
import json
with open("snapshot.json", "w") as f:
    json.dump(snapshot.__dict__, f)
```

**Service Registry Backup**:
```python
from src.launcher import get_service_registry

registry = get_service_registry()
services = await registry.get_all_services()

# Export services
import json
services_data = [s.__dict__ for s in services]
with open("services.json", "w") as f:
    json.dump(services_data, f)
```

### Scaling

**Horizontal Scaling**:
- Add more referees for parallel match execution
- Add load balancer in front of league manager
- Distribute players across multiple hosts

**Vertical Scaling**:
- Increase memory for large tournaments (100+ players)
- Increase CPU for faster match execution
- Use SSD for faster I/O

---

## Summary

This operations guide covers:
- ✅ Component-by-component startup instructions
- ✅ Complete workflow examples
- ✅ Testing and verification procedures
- ✅ Troubleshooting common issues
- ✅ Production deployment strategies

For more details:
- [QUICKSTART_MODULAR.md](QUICKSTART_MODULAR.md) - Quick start guide
- [MODULAR_ARCHITECTURE.md](MODULAR_ARCHITECTURE.md) - Architecture details
- [EDGE_CASES_MODULAR.md](docs/EDGE_CASES_MODULAR.md) - Edge case documentation
