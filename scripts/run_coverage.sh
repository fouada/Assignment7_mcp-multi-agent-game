#!/bin/bash
#
# Comprehensive Test Coverage Script
# ===================================
#
# Runs full test suite with coverage analysis and generates reports
#

set -e  # Exit on error

echo "=================================="
echo "MCP Multi-Agent Game System"
echo "Comprehensive Test Coverage Report"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MIN_COVERAGE=85
REPORT_DIR="htmlcov"
COVERAGE_FILE=".coverage"

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    print_status $RED "ERROR: pytest not found. Please install: pip install -e \".[dev]\""
    exit 1
fi

# Check if pytest-cov is installed
if ! python -c "import pytest_cov" &> /dev/null; then
    print_status $RED "ERROR: pytest-cov not found. Please install: pip install pytest-cov"
    exit 1
fi

print_status $BLUE "Step 1: Cleaning previous coverage data..."
rm -f $COVERAGE_FILE
rm -rf $REPORT_DIR
echo "✓ Cleaned"
echo ""

print_status $BLUE "Step 2: Running test suite with coverage..."
echo ""

# Run tests with coverage
pytest tests/ \
    --cov=src \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=json \
    --cov-branch \
    -v \
    --tb=short

TEST_EXIT_CODE=$?

echo ""
print_status $BLUE "Step 3: Analyzing coverage results..."
echo ""

# Extract coverage percentage
COVERAGE_PERCENT=$(python -c "
import json
try:
    with open('coverage.json', 'r') as f:
        data = json.load(f)
        total = data['totals']['percent_covered']
        print(f'{total:.2f}')
except Exception as e:
    print('0.00')
")

print_status $YELLOW "Overall Coverage: ${COVERAGE_PERCENT}%"
print_status $YELLOW "Target Coverage: ${MIN_COVERAGE}%"
echo ""

# Check if coverage meets threshold
if (( $(echo "$COVERAGE_PERCENT >= $MIN_COVERAGE" | bc -l) )); then
    print_status $GREEN "✓ Coverage threshold met!"
else
    print_status $RED "✗ Coverage below threshold (${COVERAGE_PERCENT}% < ${MIN_COVERAGE}%)"
fi

echo ""
print_status $BLUE "Step 4: Generating detailed reports..."
echo ""

# Generate coverage badge (if coverage-badge is installed)
if command -v coverage-badge &> /dev/null; then
    coverage-badge -o coverage.svg -f
    print_status $GREEN "✓ Coverage badge generated: coverage.svg"
else
    print_status $YELLOW "ℹ coverage-badge not installed (optional)"
fi

# Generate component-level coverage report
print_status $BLUE "Component-Level Coverage:"
echo "─────────────────────────────────────────────────────"

# Use Python to parse coverage.json and create component report
python << EOF
import json
import os

try:
    with open('coverage.json', 'r') as f:
        data = json.load(f)
    
    # Group by component
    components = {}
    for file_path, file_data in data['files'].items():
        # Extract component from path (e.g., src/agents/player.py -> agents)
        if file_path.startswith('src/'):
            parts = file_path.split('/')
            if len(parts) >= 2:
                component = parts[1]
                if component not in components:
                    components[component] = {'lines': 0, 'covered': 0}
                
                summary = file_data['summary']
                components[component]['lines'] += summary['num_statements']
                components[component]['covered'] += summary['covered_lines']
    
    # Print component table
    print(f"{'Component':<20} {'Lines':<10} {'Covered':<10} {'Coverage':>10}")
    print("─" * 60)
    
    for component, stats in sorted(components.items()):
        coverage = (stats['covered'] / stats['lines'] * 100) if stats['lines'] > 0 else 0
        status = '✓' if coverage >= ${MIN_COVERAGE} else '✗'
        print(f"{component:<20} {stats['lines']:<10} {stats['covered']:<10} {coverage:>9.2f}% {status}")
    
    print("─" * 60)
    
    # Overall
    total_lines = sum(c['lines'] for c in components.values())
    total_covered = sum(c['covered'] for c in components.values())
    total_coverage = (total_covered / total_lines * 100) if total_lines > 0 else 0
    print(f"{'TOTAL':<20} {total_lines:<10} {total_covered:<10} {total_coverage:>9.2f}%")
    
except FileNotFoundError:
    print("Warning: coverage.json not found")
except Exception as e:
    print(f"Error parsing coverage: {e}")
EOF

echo "─────────────────────────────────────────────────────"
echo ""

# Generate missing coverage report
print_status $BLUE "Files with < ${MIN_COVERAGE}% coverage:"
echo "─────────────────────────────────────────────────────"

python << EOF
import json

try:
    with open('coverage.json', 'r') as f:
        data = json.load(f)
    
    low_coverage = []
    for file_path, file_data in data['files'].items():
        coverage = file_data['summary']['percent_covered']
        if coverage < ${MIN_COVERAGE}:
            low_coverage.append((file_path, coverage))
    
    if low_coverage:
        low_coverage.sort(key=lambda x: x[1])
        for file_path, coverage in low_coverage:
            print(f"  {file_path}: {coverage:.2f}%")
    else:
        print("  ✓ All files meet coverage threshold!")
    
except Exception as e:
    print(f"  Error: {e}")
EOF

echo "─────────────────────────────────────────────────────"
echo ""

print_status $BLUE "Step 5: Test Summary"
echo "─────────────────────────────────────────────────────"
python << EOF
import json

try:
    # Count tests
    import os
    test_files = [f for f in os.listdir('tests') if f.startswith('test_') and f.endswith('.py')]
    print(f"Test Files: {len(test_files)}")
    
    # Parse coverage for line counts
    with open('coverage.json', 'r') as f:
        data = json.load(f)
    
    total_statements = data['totals']['num_statements']
    covered_lines = data['totals']['covered_lines']
    missing_lines = data['totals']['missing_lines']
    
    print(f"Total Statements: {total_statements}")
    print(f"Covered Lines: {covered_lines}")
    print(f"Missing Lines: {missing_lines}")
    print(f"Coverage: {data['totals']['percent_covered']:.2f}%")
    
except Exception as e:
    print(f"Error: {e}")
EOF
echo "─────────────────────────────────────────────────────"
echo ""

# Open HTML report
print_status $BLUE "Step 6: HTML Report"
echo "─────────────────────────────────────────────────────"
if [ -d "$REPORT_DIR" ]; then
    print_status $GREEN "✓ HTML report generated at: ${REPORT_DIR}/index.html"
    echo ""
    echo "To view the report, run:"
    echo "  open ${REPORT_DIR}/index.html     # macOS"
    echo "  xdg-open ${REPORT_DIR}/index.html # Linux"
    echo "  start ${REPORT_DIR}/index.html    # Windows"
else
    print_status $RED "✗ HTML report not generated"
fi

echo "─────────────────────────────────────────────────────"
echo ""

# Final status
print_status $BLUE "=================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_status $GREEN "✓ All tests passed!"
else
    print_status $RED "✗ Some tests failed (exit code: $TEST_EXIT_CODE)"
fi

if (( $(echo "$COVERAGE_PERCENT >= $MIN_COVERAGE" | bc -l) )); then
    print_status $GREEN "✓ Coverage threshold met (${COVERAGE_PERCENT}% >= ${MIN_COVERAGE}%)"
    print_status $GREEN "=================================="
    echo ""
    print_status $GREEN "🎉 SUCCESS: Project meets MIT-level quality standards!"
    exit 0
else
    print_status $RED "✗ Coverage below threshold (${COVERAGE_PERCENT}% < ${MIN_COVERAGE}%)"
    print_status $RED "=================================="
    exit 1
fi

