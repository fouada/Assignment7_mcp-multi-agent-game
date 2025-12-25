#!/bin/bash
#
# Verification Script for Testing Infrastructure
# ==============================================
#
# This script verifies that all testing infrastructure is properly set up.
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Testing Infrastructure Verification"
echo "  MCP Multi-Agent Game System"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Track results
PASSED=0
FAILED=0
WARNINGS=0

check_file() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $description"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description - Missing: $file"
        ((FAILED++))
        return 1
    fi
}

check_dir() {
    local dir=$1
    local description=$2
    
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} $description"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $description - Missing: $dir"
        ((FAILED++))
        return 1
    fi
}

check_command() {
    local cmd=$1
    local description=$2
    
    if command -v $cmd &> /dev/null; then
        echo -e "${GREEN}✓${NC} $description"
        ((PASSED++))
        return 0
    else
        echo -e "${YELLOW}⚠${NC} $description - Command not found: $cmd"
        ((WARNINGS++))
        return 1
    fi
}

echo "📁 Checking File Structure..."
echo "────────────────────────────────────────────────────────"

# CI/CD Files
check_file ".github/workflows/ci.yml" "GitHub Actions workflow"
check_file ".gitlab-ci.yml" "GitLab CI configuration"
check_file "Jenkinsfile" "Jenkins pipeline"

# Docker Files
check_file "Dockerfile.test" "Docker test image"
check_file "docker-compose.test.yml" "Docker Compose test config"

# Git Hooks
check_file ".githooks/pre-commit" "Pre-commit hook"
check_file ".githooks/pre-push" "Pre-push hook"
check_file ".githooks/install-hooks.sh" "Hook installation script"
check_file ".pre-commit-config.yaml" "Pre-commit configuration"

# Test Files
check_file "tests/conftest.py" "PyTest configuration"
check_file "tests/test_integration.py" "Integration tests"
check_file "tests/test_performance.py" "Performance tests"

# Test Utilities
check_dir "tests/utils" "Test utilities directory"
check_file "tests/utils/__init__.py" "Test utils init"
check_file "tests/utils/mocking.py" "Mocking framework"
check_file "tests/utils/factories.py" "Test data factories"
check_file "tests/utils/fixtures.py" "Test fixtures"
check_file "tests/utils/assertions.py" "Custom assertions"

# Documentation
check_file "TESTING_INFRASTRUCTURE.md" "Testing infrastructure docs"
check_file "docs/CI_CD_GUIDE.md" "CI/CD guide"
check_file "docs/EDGE_CASES_CATALOG.md" "Edge cases catalog"
check_file "docs/COMPREHENSIVE_TESTING.md" "Comprehensive testing docs"

echo ""
echo "🔧 Checking Dependencies..."
echo "────────────────────────────────────────────────────────"

check_command "python" "Python"
check_command "pytest" "PyTest"
check_command "ruff" "Ruff linter"
check_command "docker" "Docker"
check_command "git" "Git"

echo ""
echo "🧪 Running Quick Tests..."
echo "────────────────────────────────────────────────────────"

if command -v pytest &> /dev/null; then
    if pytest tests/ -m "not slow and not integration" --tb=short -q; then
        echo -e "${GREEN}✓${NC} Quick tests passed"
        ((PASSED++))
    else
        echo -e "${RED}✗${NC} Quick tests failed"
        ((FAILED++))
    fi
else
    echo -e "${YELLOW}⚠${NC} Cannot run tests - pytest not available"
    ((WARNINGS++))
fi

echo ""
echo "📊 Checking Coverage..."
echo "────────────────────────────────────────────────────────"

if command -v pytest &> /dev/null && python -c "import pytest_cov" &> /dev/null; then
    COVERAGE=$(pytest tests/ --cov=src --cov-report=term-missing 2>/dev/null | grep "TOTAL" | awk '{print $NF}' | tr -d '%')
    
    if [ ! -z "$COVERAGE" ]; then
        if (( $(echo "$COVERAGE >= 85" | bc -l) )); then
            echo -e "${GREEN}✓${NC} Coverage: ${COVERAGE}% (≥85% required)"
            ((PASSED++))
        else
            echo -e "${RED}✗${NC} Coverage: ${COVERAGE}% (<85% required)"
            ((FAILED++))
        fi
    else
        echo -e "${YELLOW}⚠${NC} Could not determine coverage"
        ((WARNINGS++))
    fi
else
    echo -e "${YELLOW}⚠${NC} Cannot check coverage - pytest-cov not available"
    ((WARNINGS++))
fi

echo ""
echo "🐳 Checking Docker Setup..."
echo "────────────────────────────────────────────────────────"

if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        echo -e "${GREEN}✓${NC} Docker is running"
        ((PASSED++))
        
        # Try to build test image
        if docker build -f Dockerfile.test -t mcp-game-test-verify --target base . &> /dev/null; then
            echo -e "${GREEN}✓${NC} Docker test image builds successfully"
            ((PASSED++))
            docker rmi mcp-game-test-verify &> /dev/null || true
        else
            echo -e "${YELLOW}⚠${NC} Docker test image build failed"
            ((WARNINGS++))
        fi
    else
        echo -e "${YELLOW}⚠${NC} Docker is installed but not running"
        ((WARNINGS++))
    fi
else
    echo -e "${YELLOW}⚠${NC} Docker not available"
    ((WARNINGS++))
fi

echo ""
echo "🪝 Checking Git Hooks..."
echo "────────────────────────────────────────────────────────"

if [ -d ".git" ]; then
    if [ -f ".git/hooks/pre-commit" ]; then
        echo -e "${GREEN}✓${NC} Pre-commit hook installed"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} Pre-commit hook not installed (run: .githooks/install-hooks.sh)"
        ((WARNINGS++))
    fi
    
    if [ -f ".git/hooks/pre-push" ]; then
        echo -e "${GREEN}✓${NC} Pre-push hook installed"
        ((PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} Pre-push hook not installed (run: .githooks/install-hooks.sh)"
        ((WARNINGS++))
    fi
else
    echo -e "${YELLOW}⚠${NC} Not a git repository"
    ((WARNINGS++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Verification Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✓ Passed:    $PASSED${NC}"
echo -e "${YELLOW}⚠ Warnings:  $WARNINGS${NC}"
echo -e "${RED}✗ Failed:    $FAILED${NC}"
echo ""

TOTAL=$((PASSED + WARNINGS + FAILED))
SUCCESS_RATE=$(echo "scale=1; $PASSED * 100 / $TOTAL" | bc)

echo "Success Rate: ${SUCCESS_RATE}%"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✅ Testing Infrastructure: VERIFIED${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "🎉 All critical components are in place!"
    echo ""
    echo "Next steps:"
    echo "  1. Install git hooks: cd .githooks && ./install-hooks.sh"
    echo "  2. Run full tests: pytest tests/ --cov=src --cov-report=html"
    echo "  3. View coverage: open htmlcov/index.html"
    echo "  4. Setup CI/CD on your platform (GitHub/GitLab/Jenkins)"
    echo ""
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  ❌ Testing Infrastructure: INCOMPLETE${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "⚠️  $FAILED critical component(s) missing!"
    echo ""
    echo "Please review the errors above and ensure all files are in place."
    echo ""
    exit 1
fi

