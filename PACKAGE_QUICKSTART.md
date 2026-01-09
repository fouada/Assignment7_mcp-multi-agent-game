# MCP Game League - Package Quick Start

**Fast-track guide for using the `mcp-game-league` Python package.**

---

## ⚡ 30-Second Install

```bash
# Install the package
pip install mcp-game-league

# Verify installation
mcp-version
```

---

## 🎮 Run Your First Game (2 Minutes)

### Terminal 1: Start League Manager

```bash
mcp-league --dashboard
```

Visit: http://localhost:8050

### Terminal 2: Start Players

```bash
# Player 1
mcp-player --port 8101 --strategy random --name "Alice"

# Player 2 (in another terminal)
mcp-player --port 8102 --strategy adaptive --name "Bob"
```

### Terminal 3: Start Referee

```bash
mcp-referee --port 8001
```

**Done!** The tournament will start automatically.

---

## 📦 Package CLI Commands

### Main Commands

| Command | Description | Example |
|---------|-------------|---------|
| `mcp-game` | Main CLI interface | `mcp-game --help` |
| `mcp-league` | Start League Manager | `mcp-league --dashboard` |
| `mcp-referee` | Start Referee Agent | `mcp-referee --port 8001` |
| `mcp-player` | Start Player Agent | `mcp-player --port 8101` |
| `mcp-version` | Show version info | `mcp-version` |

### Common Usage Patterns

```bash
# Start league with dashboard
mcp-league --dashboard --port 8000

# Start referee with custom ID
mcp-referee --id REF01 --port 8001

# Start player with specific strategy
mcp-player --strategy llm --model claude-3-sonnet --port 8101

# Start player with auto-registration
mcp-player --port 8101 --register --league-url http://localhost:8000
```

---

## 🐍 Python API Usage

### Basic Usage

```python
import asyncio
from src.agents import LeagueManager, PlayerAgent, RefereeAgent
from src.agents.strategies import AdaptiveStrategy

async def main():
    # Create league manager
    league = LeagueManager(league_id="LEAGUE_001", port=8000)
    await league.start()
    
    # Create players
    player1 = PlayerAgent(
        name="Alice",
        port=8101,
        strategy=AdaptiveStrategy()
    )
    await player1.start()
    
    # Create referee
    referee = RefereeAgent(referee_id="REF01", port=8001)
    await referee.start()
    
    # Run tournament
    await league.run_tournament()

if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced Usage

```python
from src.common.config import Config
from src.common.events import get_event_bus
from src.agents.strategies import GameTheoryStrategy

# Configure system
config = Config()
config.league.max_players = 10
config.league.rounds_per_tournament = 5

# Subscribe to events
bus = get_event_bus()

@bus.on("game_completed")
async def on_game_complete(event):
    print(f"Game {event.game_id} completed!")

# Create player with custom strategy
player = PlayerAgent(
    name="Strategic_Bot",
    port=8101,
    strategy=GameTheoryStrategy(exploration_rate=0.2)
)
```

---

## 🎯 Quick Examples

### Example 1: Run Full System

```bash
# One-liner to start everything
mcp-game league --dashboard &
sleep 2
mcp-referee --port 8001 &
mcp-player --port 8101 --strategy random &
mcp-player --port 8102 --strategy adaptive &
wait
```

### Example 2: Custom Tournament

```python
from src.agents import LeagueManager
from src.game import OddEvenGame

league = LeagueManager(league_id="CUSTOM_001")
league.set_game_type(OddEvenGame)
league.set_tournament_config(
    rounds=10,
    players_per_match=2,
    strategy="round_robin"
)
await league.start_tournament()
```

### Example 3: LLM-Powered Player

```bash
# Set API key
export ANTHROPIC_API_KEY="your-key-here"

# Start LLM player
mcp-player \
    --strategy llm \
    --model claude-3-sonnet \
    --port 8101 \
    --name "Claude_Bot"
```

---

## 🔧 Configuration

### Environment Variables

```bash
# API Keys (for LLM strategies)
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."

# Logging
export LOG_LEVEL="DEBUG"  # DEBUG, INFO, WARNING, ERROR

# Ports
export LEAGUE_PORT=8000
export REFEREE_PORT=8001
export PLAYER_PORT=8101
```

### Config File

Create `config/league.yaml`:

```yaml
league:
  league_id: "PROD_LEAGUE_001"
  max_players: 20
  rounds_per_tournament: 10
  
game:
  type: "odd_even"
  timeout: 30
  
observability:
  enable_metrics: true
  enable_tracing: true
  log_level: "INFO"
```

---

## 📚 Next Steps

1. **Read Full Documentation**: [README.md](README.md)
2. **Installation Guide**: [INSTALL.md](INSTALL.md)
3. **API Reference**: [docs/API.md](docs/API.md)
4. **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
5. **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 🆘 Common Issues

### Port Already in Use

```bash
# Find and kill process
lsof -ti:8000 | xargs kill -9

# Or use different port
mcp-league --port 8010
```

### Module Not Found

```bash
# Reinstall package
pip install --upgrade --force-reinstall mcp-game-league

# Or install from source
git clone <repo>
cd <repo>
pip install -e .
```

### Permission Denied

```bash
# Use user install
pip install --user mcp-game-league

# Or use virtual environment
python -m venv venv
source venv/bin/activate
pip install mcp-game-league
```

---

## 📞 Support

- **Issues**: https://github.com/mcp-game/mcp-multi-agent-game/issues
- **Docs**: https://github.com/mcp-game/mcp-multi-agent-game#readme
- **Email**: mcp-game@example.com

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.
