# Python Package Distribution Guide

Complete guide for building, testing, and distributing the MCP Multi-Agent Game League System as a Python package.

---

## 📦 Package Information

| Property | Value |
|----------|-------|
| **Package Name** | `mcp-game-league` |
| **Version** | `2.0.0` |
| **Python Requirement** | `>=3.11` |
| **Build System** | Hatchling |
| **Package Manager** | UV (recommended), pip |
| **License** | MIT |

---

## 🏗️ Building the Package

### Prerequisites

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or via pip
pip install uv
```

### Build with UV

```bash
# Navigate to project root
cd /path/to/mcp-multi-agent-game

# Build source distribution and wheel
uv build

# Output will be in dist/:
# - mcp-game-league-2.0.0.tar.gz (source distribution)
# - mcp-game-league-2.0.0-py3-none-any.whl (wheel)
```

### Build with Python Build

```bash
# Install build tool
pip install build

# Build the package
python -m build

# Check the built packages
ls -lh dist/
```

---

## ✅ Testing the Package

### Test Installation Locally

```bash
# Install from local wheel
uv pip install dist/mcp-game-league-2.0.0-py3-none-any.whl

# Or from source distribution
uv pip install dist/mcp-game-league-2.0.0.tar.gz

# Test the installation
mcp-version
mcp-game --help
```

### Test in Clean Environment

```bash
# Create a fresh virtual environment
python -m venv test_env
source test_env/bin/activate

# Install the package
pip install dist/mcp-game-league-2.0.0-py3-none-any.whl

# Run tests
mcp-version
mcp-league --help
mcp-player --help

# Cleanup
deactivate
rm -rf test_env
```

---

## 📤 Publishing to PyPI

### Step 1: Create PyPI Account

1. Go to https://pypi.org/account/register/
2. Create an account
3. Verify your email

### Step 2: Create API Token

1. Go to https://pypi.org/manage/account/token/
2. Create a new API token
3. Scope: Entire account (or specific project)
4. Save the token securely

### Step 3: Configure Credentials

```bash
# Create/edit ~/.pypirc
cat > ~/.pypirc << EOF
[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE
EOF

# Secure the file
chmod 600 ~/.pypirc
```

### Step 4: Upload to TestPyPI (Recommended First)

```bash
# Install twine
uv pip install twine

# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ mcp-game-league
```

### Step 5: Upload to PyPI

```bash
# Upload to production PyPI
python -m twine upload dist/*

# Verify on PyPI
# Visit: https://pypi.org/project/mcp-game-league/
```

---

## 🔍 Package Verification

### Check Package Metadata

```bash
# Using twine
twine check dist/*

# Expected output:
# Checking dist/mcp-game-league-2.0.0.tar.gz: PASSED
# Checking dist/mcp-game-league-2.0.0-py3-none-any.whl: PASSED
```

### Inspect Package Contents

```bash
# View wheel contents
unzip -l dist/mcp-game-league-2.0.0-py3-none-any.whl

# View source distribution contents
tar -tzf dist/mcp-game-league-2.0.0.tar.gz
```

### Test CLI Entry Points

```bash
# After installation, test all entry points
mcp-version          # Should display version info
mcp-game --help      # Main CLI help
mcp-league --help    # League manager help
mcp-referee --help   # Referee help
mcp-player --help    # Player help
```

---

## 📋 Pre-Release Checklist

Before publishing a new version:

- [ ] Update version in `pyproject.toml`
- [ ] Update version in `src/__init__.py`
- [ ] Update `CHANGELOG.md` with release notes
- [ ] Run full test suite: `pytest`
- [ ] Check code quality: `ruff check src/`
- [ ] Check types: `mypy src/`
- [ ] Build package: `uv build`
- [ ] Verify package: `twine check dist/*`
- [ ] Test local installation
- [ ] Update documentation
- [ ] Tag release in git: `git tag v2.0.0`
- [ ] Push tags: `git push --tags`

---

## 🔄 Version Management

### Semantic Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (2.x.x): Breaking changes
- **MINOR** (x.1.x): New features, backward compatible
- **PATCH** (x.x.1): Bug fixes, backward compatible

### Updating Version

```bash
# Update in pyproject.toml
[project]
version = "2.1.0"  # New version

# Update in src/__init__.py
__version__ = "2.1.0"

# Update CHANGELOG.md
## [2.1.0] - 2025-01-15
### Added
- New feature X
...

# Commit changes
git add pyproject.toml src/__init__.py CHANGELOG.md
git commit -m "chore: bump version to 2.1.0"

# Tag release
git tag -a v2.1.0 -m "Release version 2.1.0"
git push origin main --tags
```

---

## 🚀 Automated Release with GitHub Actions

### Create Release Workflow

```yaml
# .github/workflows/release.yml
name: Release to PyPI

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install UV
        run: pip install uv
      
      - name: Build package
        run: uv build
      
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: |
          pip install twine
          twine upload dist/*
```

### Configure Secrets

1. Go to GitHub repository settings
2. Navigate to Secrets and variables → Actions
3. Add new secret: `PYPI_API_TOKEN`
4. Paste your PyPI API token

---

## 📦 Package Structure

```
mcp-game-league/
├── src/                          # Source code
│   ├── __init__.py              # Package metadata
│   ├── cli.py                   # CLI entry points
│   ├── agents/                  # Agent implementations
│   ├── common/                  # Shared utilities
│   ├── game/                    # Game logic
│   └── ...
├── tests/                        # Test suite
├── docs/                         # Documentation
├── examples/                     # Example scripts
├── config/                       # Configuration files
├── pyproject.toml               # Package configuration
├── MANIFEST.in                  # Include additional files
├── README.md                    # Project README
├── LICENSE                      # MIT License
├── CHANGELOG.md                 # Version history
├── INSTALL.md                   # Installation guide
└── PACKAGING.md                 # This file
```

---

## 🔧 Package Configuration

### pyproject.toml Key Sections

```toml
[project]
name = "mcp-game-league"
version = "2.0.0"
description = "Production-Grade MCP Multi-Agent Game League System"
requires-python = ">=3.11"

[project.scripts]
mcp-game = "src.cli:main"
mcp-league = "src.cli:main_league"
mcp-referee = "src.cli:main_referee"
mcp-player = "src.cli:main_player"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]
```

### MANIFEST.in

```
include README.md LICENSE CHANGELOG.md
recursive-include config *.yaml *.json
recursive-include docs *.md *.png
recursive-include examples *.py *.sh
global-exclude *.pyc __pycache__ *.log
```

---

## 🐛 Troubleshooting

### Build Fails

```bash
# Error: No module named 'hatchling'
# Solution: Install build dependencies
pip install hatchling

# Or use UV which handles this automatically
uv build
```

### Upload Fails

```bash
# Error: 403 Forbidden
# Solution: Check your API token
# 1. Verify token in ~/.pypirc
# 2. Ensure token has correct permissions
# 3. Try re-creating the token
```

### Package Not Found After Upload

```bash
# Wait a few minutes for PyPI to index
# Then try:
pip install --upgrade mcp-game-league

# Or clear pip cache:
pip cache purge
pip install mcp-game-league
```

---

## 📊 Package Statistics

After publishing, monitor your package:

- **PyPI Page**: https://pypi.org/project/mcp-game-league/
- **Download Stats**: https://pypistats.org/packages/mcp-game-league
- **GitHub Releases**: https://github.com/mcp-game/mcp-multi-agent-game/releases

---

## 🔐 Security

### Package Signing

```bash
# Sign the package with GPG
gpg --detach-sign -a dist/mcp-game-league-2.0.0.tar.gz

# Upload signature
twine upload dist/* dist/*.asc
```

### Vulnerability Scanning

```bash
# Scan for security issues
pip install safety
safety check --file pyproject.toml

# Or use bandit
bandit -r src/
```

---

## 📚 Additional Resources

- **PyPI Documentation**: https://packaging.python.org/
- **UV Documentation**: https://github.com/astral-sh/uv
- **Hatchling**: https://hatch.pypa.io/
- **Twine**: https://twine.readthedocs.io/
- **Semantic Versioning**: https://semver.org/

---

## 🤝 Contributing to Package

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

---

## 📞 Support

- **Issues**: https://github.com/mcp-game/mcp-multi-agent-game/issues
- **Email**: mcp-game@example.com

---

## License

MIT License - see [LICENSE](LICENSE) file for details.
