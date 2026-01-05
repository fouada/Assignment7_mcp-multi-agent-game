# 🚀 Getting Started

## Overview

This folder contains everything you need to get up and running quickly. Perfect for new users and first-time contributors.

---

## ⭐ Featured: Prompt Engineering

**[→ Prompt Engineering Start Here](PROMPT_ENGINEERING_START_HERE.md)** - Gateway to the world's most comprehensive prompt engineering documentation for multi-agent systems

- 📖 50,000+ words of documentation
- 🎯 15+ production-tested prompts
- 🔬 5 research findings with statistical validation
- 💻 80+ code examples
- 📊 25+ diagrams

---

## 📚 Documents

| Document | Purpose | Audience | Read Time |
|----------|---------|----------|-----------|
| [PROMPT_ENGINEERING_START_HERE.md](PROMPT_ENGINEERING_START_HERE.md) ⭐ | Gateway to prompt engineering docs | Developers, Researchers | 5 min |
| [START_HERE.md](START_HERE.md) | General quick start guide | All users | 5 min |
| [HOW_TO_START_TOURNAMENT.md](HOW_TO_START_TOURNAMENT.md) | Tournament setup guide | Operators | 10 min |
| [QUICKSTART_MODULAR.md](QUICKSTART_MODULAR.md) | Modular system quick start | Developers | 15 min |
| [REQUIREMENTS.md](REQUIREMENTS.md) | System requirements & dependencies | All users | 10 min |
| [SCREENSHOT_GUIDE.md](SCREENSHOT_GUIDE.md) | Visual guide with screenshots | All users | 10 min |

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

