# 🚀 Getting Started

## Overview

This folder contains everything you need to get up and running quickly. Perfect for new users and first-time contributors.

## 📚 Documents

| Document | Purpose | Audience | Read Time |
|----------|---------|----------|-----------|
| [REQUIREMENTS.md](REQUIREMENTS.md) | System requirements & dependencies | All users | 10 min |

## 🎯 Quick Start Guide

### 1. Prerequisites

See [REQUIREMENTS.md](REQUIREMENTS.md) for:
- Python 3.11+
- System dependencies
- Optional tools

### 2. Installation

```bash
# Clone the repository
git clone <repo-url>
cd mcp-game-league

# Install dependencies
pip install -e .

# Verify installation
make test
```

### 3. First Run

```bash
# Run a quick tournament
./scripts/run_league.sh

# View the dashboard
python examples/dashboard/run_with_dashboard.py
```

### 4. Next Steps

- Read the [Development Guide](../guides/DEVELOPMENT.md)
- Explore [Architecture](../architecture/)
- Try the [Innovations](../research/)

## 📖 Essential Reading

1. **[../../README.md](../../README.md)** - Main project overview
2. **[../../START_HERE.md](../../START_HERE.md)** - 5-minute orientation
3. **[../DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md)** - Complete doc index

## 🔧 Common Commands

```bash
# Run tests
make test

# Run with coverage
./scripts/run_coverage.sh

# Start dashboard
python examples/dashboard/run_with_dashboard.py

# Run league
./scripts/run_league.sh

# Verify compliance
./scripts/verify_compliance.sh
```

## 🆘 Getting Help

- **Documentation**: See [../DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md)
- **API Reference**: See [../api/](../api/)
- **Troubleshooting**: See [../guides/DEVELOPMENT.md](../guides/DEVELOPMENT.md)

## 🔗 Related Documentation

- [Guides](../guides/) - Detailed guides
- [API](../api/) - API reference
- [Testing](../testing/) - Testing info

---

*For complete documentation navigation, see [DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md)*

