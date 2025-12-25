# CI/CD Guide
## Comprehensive Continuous Integration and Deployment

---

## Overview

This guide covers the complete CI/CD infrastructure for the MCP Multi-Agent Game System, including:
- GitHub Actions workflows
- GitLab CI pipelines
- Jenkins pipelines
- Pre-commit hooks
- Docker-based testing
- Deployment strategies

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [GitHub Actions](#github-actions)
3. [GitLab CI](#gitlab-ci)
4. [Jenkins](#jenkins)
5. [Pre-Commit Hooks](#pre-commit-hooks)
6. [Docker Testing](#docker-testing)
7. [Local Testing](#local-testing)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Install Pre-Commit Hooks

```bash
# Install pre-commit tool
pip install pre-commit

# Install hooks
pre-commit install

# Or use custom hooks
cd .githooks
chmod +x install-hooks.sh
./install-hooks.sh
```

### Run Tests Locally

```bash
# Quick tests
pytest tests/ -v -m "not slow and not integration"

# Full test suite
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# Using script
./scripts/run_tests.sh --coverage
```

### Run Tests in Docker

```bash
# Build and run all tests
docker-compose -f docker-compose.test.yml up

# Run specific test suite
docker-compose -f docker-compose.test.yml run unit-tests
docker-compose -f docker-compose.test.yml run integration-tests
docker-compose -f docker-compose.test.yml run performance-tests

# View coverage report
docker-compose -f docker-compose.test.yml up coverage-server
# Open http://localhost:8080 in browser
```

---

## GitHub Actions

### Workflows

The project includes a comprehensive GitHub Actions workflow in `.github/workflows/ci.yml`:

#### Jobs Overview

1. **lint-and-format** - Code quality checks
   - Ruff linting
   - Ruff formatting
   - MyPy type checking
   - Bandit security scanning

2. **unit-tests** - Fast unit tests
   - Runs on: Ubuntu, macOS, Windows
   - Python: 3.11, 3.12
   - Matrix testing for compatibility

3. **coverage** - Coverage analysis
   - Minimum 85% coverage required
   - Generates HTML and XML reports
   - Uploads to Codecov
   - Posts PR comments with coverage

4. **integration-tests** - End-to-end tests
   - Full system integration
   - Multi-agent scenarios
   - Timeout: 15 minutes

5. **performance-tests** - Performance benchmarks
   - Load testing
   - Stress testing
   - Benchmark comparisons

6. **security-scan** - Security checks
   - Safety vulnerability scanning
   - pip-audit dependency audit
   - SAST analysis

7. **docker-test** - Docker build and test
   - Multi-stage builds
   - Container testing
   - Image validation

8. **mutation-testing** - Test quality check
   - Mutmut mutation testing
   - Validates test effectiveness

### Triggering Workflows

```yaml
# Automatic triggers
on:
  push:
    branches: [ main, develop, feature/** ]
  pull_request:
    branches: [ main, develop ]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC

# Manual trigger
workflow_dispatch:
```

### Required Secrets

```bash
# Add to GitHub repository secrets
CODECOV_TOKEN=<your-codecov-token>
```

### Badge Integration

```markdown
![CI](https://github.com/username/repo/workflows/CI/badge.svg)
![Coverage](https://codecov.io/gh/username/repo/branch/main/graph/badge.svg)
```

---

## GitLab CI

### Pipeline Configuration

The GitLab CI pipeline is defined in `.gitlab-ci.yml`:

#### Stages

1. **validate** - Linting and type checking
2. **test** - Unit, integration, and performance tests
3. **security** - Security scanning
4. **quality** - Code quality metrics
5. **report** - Generate and publish reports
6. **deploy** - Deployment gate

### Features

- **Caching**: Efficient dependency caching
- **Artifacts**: Test reports and coverage
- **Pages**: Published coverage reports
- **Matrix Builds**: Multiple Python versions
- **Docker**: Containerized testing

### Running Locally

```bash
# Install gitlab-runner
curl -L https://packages.gitlab.com/install/repositories/runner/gitlab-runner/script.deb.sh | sudo bash
sudo apt-get install gitlab-runner

# Test pipeline locally
gitlab-runner exec docker test:unit:python311
```

### Pipeline Variables

```yaml
# Set in GitLab CI/CD settings
PYTHON_VERSION: "3.11"
MIN_COVERAGE: "85"
```

---

## Jenkins

### Pipeline Configuration

The Jenkins pipeline is defined in `Jenkinsfile`:

#### Stages Overview

1. **Setup** - Environment preparation
2. **Validate** - Parallel linting and type checking
3. **Test** - Parallel test execution
4. **Coverage** - Coverage analysis with reports
5. **Security Scan** - Vulnerability scanning
6. **Quality Metrics** - Code quality analysis
7. **Docker Build** - Container building
8. **Deployment Gate** - Release validation

### Features

- **Parallel Execution**: Fast CI with parallelization
- **HTML Reports**: Published coverage and test reports
- **Cobertura**: Coverage visualization
- **Build Artifacts**: Saved reports and logs
- **Email Notifications**: Success/failure alerts

### Installation

```bash
# Add Jenkins credentials
- CODECOV_TOKEN
- GITHUB_TOKEN (for PR comments)

# Install required plugins
- Pipeline
- HTML Publisher
- Cobertura
- JUnit
- AnsiColor
```

### Running Pipeline

```groovy
// Jenkinsfile parameters
parameters {
    booleanParam(name: 'SKIP_TESTS', defaultValue: false, description: 'Skip tests')
    booleanParam(name: 'SKIP_SECURITY', defaultValue: false, description: 'Skip security scan')
}
```

---

## Pre-Commit Hooks

### Installation

```bash
# Method 1: Using pre-commit tool
pip install pre-commit
pre-commit install

# Method 2: Custom git hooks
cd .githooks
./install-hooks.sh
```

### Hooks Available

#### Pre-Commit Hook

Runs before each commit:
1. Ruff linting (auto-fix)
2. Ruff formatting
3. MyPy type checking
4. Bandit security scan
5. Quick unit tests
6. Coverage check (optional)

#### Pre-Push Hook

Runs before pushing:
1. Full test suite
2. Coverage validation (85%+)
3. Integration tests
4. Security scan
5. Dependency check

### Configuration

Located in `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
```

### Skipping Hooks

```bash
# Skip pre-commit hooks
git commit --no-verify

# Skip pre-push hooks
git push --no-verify

# Skip specific hook
SKIP=pytest-check git commit -m "message"
```

### Updating Hooks

```bash
# Update to latest versions
pre-commit autoupdate

# Run on all files
pre-commit run --all-files
```

---

## Docker Testing

### Test Containers

#### Unit Tests

```bash
docker-compose -f docker-compose.test.yml run unit-tests
```

#### Integration Tests

```bash
docker-compose -f docker-compose.test.yml run integration-tests
```

#### Performance Tests

```bash
docker-compose -f docker-compose.test.yml run performance-tests
```

#### Quick Tests (CI)

```bash
docker-compose -f docker-compose.test.yml run quick-tests
```

### Multi-Stage Builds

The `Dockerfile.test` uses multi-stage builds:

1. **base** - Base Python image
2. **dependencies** - Install dependencies
3. **test-env** - Setup test environment
4. **test-runner** - Run all tests
5. **quick-tests** - Fast CI tests
6. **integration-tests** - Integration tests
7. **performance-tests** - Performance benchmarks

### Volume Mounts

```yaml
volumes:
  - ./test-reports:/app/test-reports  # Test results
  - ./htmlcov:/app/htmlcov            # Coverage reports
```

### Coverage Report Server

```bash
# Start coverage report server
docker-compose -f docker-compose.test.yml up coverage-server

# Access at http://localhost:8080
```

---

## Local Testing

### Quick Tests

```bash
# Fast tests only
pytest tests/ -m "not slow and not integration"

# With verbose output
pytest tests/ -v -m "not slow"

# Stop on first failure
pytest tests/ -x -m "not slow"
```

### Full Test Suite

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=term-missing

# Parallel execution
pytest tests/ -n auto
```

### Specific Tests

```bash
# Single file
pytest tests/test_player_agent.py -v

# Single class
pytest tests/test_player_agent.py::TestPlayerAgentInitialization -v

# Single test
pytest tests/test_player_agent.py::TestPlayerAgentInitialization::test_player_init_basic -v

# By marker
pytest tests/ -m integration
pytest tests/ -m slow
pytest tests/ -m benchmark
```

### Coverage Reports

```bash
# Generate HTML report
pytest tests/ --cov=src --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# Generate multiple reports
pytest tests/ \
  --cov=src \
  --cov-report=html \
  --cov-report=xml \
  --cov-report=term-missing
```

### Performance Tests

```bash
# Run performance tests
pytest tests/ -m "slow or benchmark" -v

# With benchmarking
pytest tests/ -m benchmark --benchmark-only

# Save benchmark results
pytest tests/ -m benchmark --benchmark-json=output.json
```

---

## Troubleshooting

### Common Issues

#### 1. Pre-Commit Hook Fails

**Problem**: Hook fails with import errors

**Solution**:
```bash
# Reinstall dependencies
pip install -e ".[dev]"

# Update pre-commit
pre-commit clean
pre-commit install
```

#### 2. Docker Build Fails

**Problem**: Cannot build Docker image

**Solution**:
```bash
# Clean Docker cache
docker system prune -a

# Rebuild without cache
docker-compose -f docker-compose.test.yml build --no-cache
```

#### 3. Coverage Below Threshold

**Problem**: Coverage is below 85%

**Solution**:
```bash
# Identify missing coverage
pytest tests/ --cov=src --cov-report=term-missing

# Focus on specific file
pytest tests/ --cov=src/agents/player.py --cov-report=term-missing
```

#### 4. Tests Hang

**Problem**: Tests don't complete

**Solution**:
```bash
# Add timeout
pytest tests/ --timeout=300

# Find slow tests
pytest tests/ --durations=10
```

#### 5. Integration Tests Fail

**Problem**: Integration tests fail locally

**Solution**:
```bash
# Check if services are running
docker-compose ps

# Start required services
docker-compose up -d

# Run integration tests
pytest tests/ -m integration
```

### Debug Mode

```bash
# Run with debug output
pytest tests/ -vv --log-cli-level=DEBUG

# Drop into debugger on failure
pytest tests/ --pdb

# Show print statements
pytest tests/ -s
```

### Performance Issues

```bash
# Profile test execution
pytest tests/ --profile

# Show slowest tests
pytest tests/ --durations=20

# Parallel execution
pytest tests/ -n 4  # 4 workers
pytest tests/ -n auto  # Auto-detect
```

---

## Best Practices

### 1. Commit Frequently

```bash
# Make small, focused commits
git commit -m "Add player registration test"
git commit -m "Fix move validation edge case"
```

### 2. Keep Tests Fast

- Mark slow tests with `@pytest.mark.slow`
- Use mocking for external dependencies
- Run quick tests during development

### 3. Maintain Coverage

- Aim for 85%+ coverage
- Test edge cases thoroughly
- Document untestable code with `# pragma: no cover`

### 4. Use CI Feedback

- Review CI logs for failures
- Fix broken tests immediately
- Don't merge failing PRs

### 5. Security First

- Run security scans regularly
- Update dependencies
- Review security alerts

---

## Continuous Deployment

### Deployment Strategies

#### 1. Blue-Green Deployment

```yaml
# GitHub Actions
- name: Deploy to Production
  if: github.ref == 'refs/heads/main'
  run: ./scripts/deploy.sh --strategy=blue-green
```

#### 2. Canary Deployment

```yaml
# GitLab CI
deploy:canary:
  stage: deploy
  script:
    - ./scripts/deploy.sh --strategy=canary --percentage=10
```

#### 3. Rolling Deployment

```yaml
# Jenkins
stage('Deploy') {
    when {
        branch 'main'
    }
    steps {
        sh './scripts/deploy.sh --strategy=rolling'
    }
}
```

### Deployment Gates

All CI checks must pass:
- ✅ Unit tests
- ✅ Integration tests
- ✅ Coverage >= 85%
- ✅ Security scan
- ✅ Performance benchmarks

---

## Monitoring and Alerts

### CI/CD Metrics

Track these metrics:
- Build success rate
- Test pass rate
- Average build time
- Coverage trends
- Security vulnerabilities

### Alerts

Configure alerts for:
- Failed builds
- Coverage drops
- Security issues
- Performance regressions

---

## Resources

### Documentation

- [GitHub Actions Docs](https://docs.github.com/actions)
- [GitLab CI Docs](https://docs.gitlab.com/ee/ci/)
- [Jenkins Docs](https://www.jenkins.io/doc/)
- [Pre-Commit Docs](https://pre-commit.com/)

### Tools

- [Codecov](https://codecov.io/)
- [SonarQube](https://www.sonarqube.org/)
- [Dependabot](https://github.com/dependabot)

---

**Last Updated**: December 25, 2025  
**Version**: 1.0.0  
**Status**: Production Ready ✓

