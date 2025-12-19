# Deployment Guide

This guide covers deployment options for the MCP Multi-Agent Game League system.

---

## Table of Contents

- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Environment Configuration](#environment-configuration)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites

- Python 3.11+
- UV package manager
- Git

### Setup

```bash
# Clone repository
git clone <repository-url>
cd MCP_Multi_Agent_Game

# Run setup script (installs UV if needed)
./scripts/setup.sh

# Or manual setup
uv sync --all-extras

# Verify installation
uv run python -c "import src; print('Setup successful!')"
```

### Running Locally

```bash
# Start all components with 4 players
uv run python -m src.main --run --players 4

# Or run individual components
# Terminal 1 - League Manager
uv run python -m src.main --component league

# Terminal 2 - Referee
uv run python -m src.main --component referee

# Terminal 3 - Player
uv run python -m src.main --component player --name "Bot1" --port 8101 --register
```

---

## Docker Deployment

### Single Container

```bash
# Build image
docker build -t mcp-game-league .

# Run container
docker run -p 8000:8000 -p 8001:8001 \
  -e LOG_LEVEL=INFO \
  mcp-game-league

# Run with environment file
docker run --env-file .env -p 8000:8000 -p 8001:8001 mcp-game-league
```

### Docker Compose (Recommended)

```bash
# Start all services
docker-compose up --build -d

# View logs
docker-compose logs -f

# Scale players
docker-compose up --scale player1=1 --scale player2=1 --scale player3=1 --scale player4=1 -d

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Docker Compose Configuration

```yaml
# docker-compose.yml
version: '3.8'

services:
  league-manager:
    build: .
    command: ["python", "-m", "src.main", "--component", "league"]
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  referee:
    build: .
    command: ["python", "-m", "src.main", "--component", "referee"]
    ports:
      - "8001:8001"
    depends_on:
      - league-manager
    environment:
      - LEAGUE_HOST=league-manager
      - LOG_LEVEL=INFO

  player1:
    build: .
    command: ["python", "-m", "src.main", "--component", "player", "--name", "Player1", "--port", "8101", "--register"]
    ports:
      - "8101:8101"
    depends_on:
      - league-manager
      - referee
```

---

## Production Deployment

### Architecture Overview

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │     (nginx)     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ League Manager│   │    Referee    │   │   Players     │
│   (Port 8000) │   │  (Port 8001)  │   │ (Port 81XX)   │
└───────────────┘   └───────────────┘   └───────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼────────┐
                    │    Database     │
                    │   (Optional)    │
                    └─────────────────┘
```

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/mcp-game

upstream league_manager {
    server localhost:8000;
}

upstream referee {
    server localhost:8001;
}

server {
    listen 80;
    server_name your-domain.com;

    # League Manager
    location /league/ {
        proxy_pass http://league_manager/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Referee
    location /referee/ {
        proxy_pass http://referee/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Health check endpoint
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
```

### Systemd Service

```ini
# /etc/systemd/system/mcp-league.service

[Unit]
Description=MCP Game League Manager
After=network.target

[Service]
Type=simple
User=mcp
WorkingDirectory=/opt/mcp-game
ExecStart=/opt/mcp-game/.venv/bin/python -m src.main --component league
Restart=always
RestartSec=10
Environment=LOG_LEVEL=INFO
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable mcp-league
sudo systemctl start mcp-league
sudo systemctl status mcp-league
```

---

## Environment Configuration

### Required Environment Variables

```bash
# .env file
# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Server Configuration
LEAGUE_HOST=localhost
LEAGUE_PORT=8000
REFEREE_HOST=localhost
REFEREE_PORT=8001

# LLM Configuration (optional, for AI strategies)
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=your-key-here

# Game Configuration
MAX_PLAYERS=100
MATCH_TIMEOUT_SECONDS=300
MOVE_TIMEOUT_SECONDS=30

# Security
SECRET_KEY=your-secret-key-here
```

### Configuration File

```json
// config/servers.json
{
  "league_manager": {
    "host": "localhost",
    "port": 8000,
    "endpoint": "/mcp",
    "timeout": 30,
    "retry_attempts": 3
  },
  "referee": {
    "host": "localhost",
    "port": 8001,
    "endpoint": "/mcp",
    "timeout": 30
  },
  "game": {
    "type": "even_odd",
    "rounds_to_win": 3,
    "max_rounds": 5,
    "move_timeout": 30
  }
}
```

---

## Monitoring & Logging

### Log Configuration

```python
# Structured logging format
{
    "timestamp": "2024-12-13T10:00:00Z",
    "level": "INFO",
    "service": "league_manager",
    "message": "Player registered",
    "data": {
        "player_id": "P01",
        "player_name": "AlphaBot"
    }
}
```

### Health Checks

Each component exposes a `/health` endpoint:

```bash
# Check League Manager
curl http://localhost:8000/health

# Check Referee
curl http://localhost:8001/health

# Check Player
curl http://localhost:8101/health
```

### Metrics (Optional)

For production, consider adding:

- Request count per endpoint
- Response time percentiles
- Error rates
- Active connections
- Game completion rates

---

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uv run python -m src.main --component league --port 9000
```

#### Connection Refused

1. Check if service is running:
```bash
docker-compose ps
# or
curl http://localhost:8000/health
```

2. Check logs:
```bash
docker-compose logs league-manager
```

3. Verify network connectivity:
```bash
docker network ls
docker network inspect mcp-game_default
```

#### Protocol Mismatch

Ensure all components use the same protocol version:
```json
{
  "protocol": "league.v1"
}
```

#### Timeout Issues

Increase timeout values:
```bash
export MOVE_TIMEOUT_SECONDS=60
export MATCH_TIMEOUT_SECONDS=600
```

### Debug Mode

```bash
# Run with debug logging
LOG_LEVEL=DEBUG uv run python -m src.main --run --players 4

# Or in Docker
docker-compose up -e LOG_LEVEL=DEBUG
```

### Log Locations

| Deployment | Log Location |
|------------|--------------|
| Local | stdout/stderr |
| Docker | `docker-compose logs` |
| Systemd | `journalctl -u mcp-league` |

---

## Security Considerations

### Production Checklist

- [ ] Use HTTPS in production
- [ ] Set strong SECRET_KEY
- [ ] Enable rate limiting
- [ ] Configure firewall rules
- [ ] Use non-root Docker user
- [ ] Enable audit logging
- [ ] Regular security updates

### Docker Security

```dockerfile
# Run as non-root user
USER mcp

# Read-only filesystem where possible
RUN chmod -R 555 /app/src

# Limit resources
# In docker-compose.yml:
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 512M
```

---

## Backup & Recovery

### State Backup

```bash
# Backup game state (if using persistent storage)
docker-compose exec league-manager tar czf /backup/state.tar.gz /app/data

# Restore
docker cp state.tar.gz league-manager:/backup/
docker-compose exec league-manager tar xzf /backup/state.tar.gz -C /
```

### Database Backup (if applicable)

```bash
# PostgreSQL example
pg_dump -h localhost -U mcp mcp_league > backup.sql
```

---

*Last Updated: December 2024*

