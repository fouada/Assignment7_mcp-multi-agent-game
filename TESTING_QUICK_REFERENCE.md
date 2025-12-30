# Testing Quick Reference Guide
## MCP Multi-Agent Game System - Fast Access to Testing Commands

**Version:** 1.0.0  
**Last Updated:** December 30, 2025

---

## 🚀 Quick Commands

### Run All Tests

```bash
# Fast tests (< 20 seconds)
uv run pytest tests/ -v -m "not slow"

# All tests including slow
uv run pytest tests/ -v

# With coverage
uv run pytest tests/ --cov=src --cov-report=term-missing
```

### Run Specific Tests

```bash
# Single file
uv run pytest tests/test_player_agent.py -v

# Single class
uv run pytest tests/test_player_agent.py::TestPlayerAgentInitialization -v

# Single test
uv run pytest tests/test_player_agent.py::TestPlayerAgentInitialization::test_player_init_basic -v

# By marker
uv run pytest tests/ -m integration
uv run pytest tests/ -m slow
uv run pytest tests/ -m benchmark
```

### Coverage Commands

```bash
# Generate coverage report
./scripts/run_coverage.sh

# Quick coverage check
uv run pytest tests/ --cov=src --cov-report=term

# HTML coverage report
uv run pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html  # macOS
```

### Docker Testing

```bash
# Quick tests in Docker
docker compose -f docker-compose.test.yml run quick-tests

# All test suites
docker compose -f docker-compose.test.yml up

# Coverage report server
docker compose -f docker-compose.test.yml up coverage-server
# View at http://localhost:8080
```

---

## 📊 Current Status

```
Coverage:  79% (Target: 85%)
Tests:     702/732 passing (96%)
Edge Cases: 272+ documented
CI/CD:     Fully automated
```

---

## 🎯 Coverage Gaps

| Component | Current | Target | Gap |
|-----------|---------|--------|-----|
| League Manager | 63% | 85% | 22% |
| Referee Agent | 70% | 85% | 15% |
| Tracing | 60% | 85% | 25% |
| Classic Strategies | 64% | 85% | 21% |

---

## 🔧 Common Issues

### Issue: Tests Fail with Import Error

**Solution:**
```bash
uv sync --all-extras
uv run pytest tests/ -v
```

### Issue: Coverage Below Threshold

**Solution:**
```bash
# Identify missing coverage
uv run pytest tests/ --cov=src --cov-report=term-missing

# Focus on specific file
uv run pytest tests/test_league_manager_agent.py -v --cov=src/agents/league_manager.py
```

### Issue: Tracing Tests Failing

**Known Issue:** Async context manager implementation  
**Status:** 27 tests affected  
**Workaround:** 
```bash
# Skip tracing tests
uv run pytest tests/ -v -m "not slow" --ignore=tests/test_tracing.py
```

---

## 📚 Documentation

- **Testing Guide:** `docs/COMPREHENSIVE_TESTING.md`
- **Testing Flows:** `docs/TESTING_FLOWS.md`
- **Edge Cases:** `docs/EDGE_CASES_CATALOG.md`
- **CI/CD Guide:** `docs/CI_CD_GUIDE.md`
- **Assessment:** `MIT_TESTING_ASSESSMENT.md`

---

## 🔄 CI/CD Status

### GitHub Actions
- Workflow: `.github/workflows/ci.yml`
- Triggers: Push, PR, Daily 2AM UTC
- Coverage Threshold: 80%

### GitLab CI
- Pipeline: `.gitlab-ci.yml`
- Stages: validate, test, security, quality, report, deploy
- Coverage Threshold: 85%

### Jenkins
- Pipeline: `Jenkinsfile`
- Parallel execution
- HTML reports published

---

## 🎯 Next Steps to MIT Level

1. **Fix Failing Tests** (6 hours)
   - Fix async context manager in tracing
   - Update launcher test mocks

2. **Increase Coverage** (2-3 days)
   - League Manager: 63% → 85%
   - Referee Agent: 70% → 85%
   - Classic Strategies: 64% → 85%

3. **Verify** (1 hour)
   - Run full test suite
   - Generate coverage report
   - Update documentation

**Total Time to MIT Level: ~4 days**

---

## 📞 Quick Access

| What | Where |
|------|-------|
| Run tests | `uv run pytest tests/ -v` |
| Coverage | `./scripts/run_coverage.sh` |
| Docker tests | `docker compose -f docker-compose.test.yml up` |
| CI config | `.github/workflows/ci.yml` |
| Test docs | `docs/COMPREHENSIVE_TESTING.md` |
| Edge cases | `docs/EDGE_CASES_CATALOG.md` |
| This guide | `TESTING_QUICK_REFERENCE.md` |
| Full assessment | `MIT_TESTING_ASSESSMENT.md` |

---

**Quick Tip:** Bookmark this file for fast access to testing commands!

