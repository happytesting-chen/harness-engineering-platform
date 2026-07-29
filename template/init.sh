#!/usr/bin/env bash
# init.sh — Project verification script
# Auto-detects project type, runs tests, checks for unfilled placeholders,
# and verifies progress.md freshness.
#
# Exit 0 = healthy. Non-zero = issues found.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ERRORS=0
WARNINGS=0

echo "═══════════════════════════════════════════════════"
echo "  Harness Engineering Platform — init.sh"
echo "═══════════════════════════════════════════════════"
echo ""

# --- 1. Project Type Detection ---
echo "▶ Detecting project type..."
if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
    PROJECT_TYPE="python"
    echo "  Detected: Python"
elif [ -f "package.json" ]; then
    PROJECT_TYPE="node"
    echo "  Detected: Node.js"
else
    PROJECT_TYPE="other"
    echo "  Detected: Other (generic)"
fi
echo ""

# --- 2. Check for unfilled {{placeholders}} in required config files ---
echo "▶ Checking for unfilled placeholders..."
REQUIRED_FILES=("CLAUDE.md" "feature_list.json" "governance/deny-list.json" "tools/mcp-allowlist.json")
for f in "${REQUIRED_FILES[@]}"; do
    if [ -f "$f" ]; then
        PLACEHOLDERS=$(grep -o '{{[^}]*}}' "$f" 2>/dev/null || true)
        if [ -n "$PLACEHOLDERS" ]; then
            echo "  ✗ UNFILLED placeholders in $f:"
            echo "$PLACEHOLDERS" | sed 's/^/      /'
            ERRORS=$((ERRORS + 1))
        else
            echo "  ✓ $f — no placeholders"
        fi
    else
        echo "  ✗ MISSING required file: $f"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

# --- 3. Check progress.md staleness ---
echo "▶ Checking progress.md freshness..."
if [ -f "progress.md" ]; then
    PROGRESS_MTIME=$(stat -f %m "progress.md" 2>/dev/null || stat -c %Y "progress.md" 2>/dev/null || echo "0")
    # Find most recently modified .py or .json file
    LATEST_CODE=$(find . -name "*.py" -o -name "*.json" -o -name "*.md" | \
                  grep -v progress.md | grep -v node_modules | \
                  xargs stat -f %m 2>/dev/null | sort -n | tail -1 || echo "0")
    if [ -n "$LATEST_CODE" ] && [ "$PROGRESS_MTIME" -lt "$LATEST_CODE" ] 2>/dev/null; then
        echo "  ⚠ WARNING: progress.md is older than recent code changes"
        WARNINGS=$((WARNINGS + 1))
    else
        echo "  ✓ progress.md is up to date"
    fi
else
    echo "  ⚠ WARNING: progress.md not found"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# --- 4. Run fixture-based tests ---
echo "▶ Running tests..."
if [ -f "tests/test_fixtures.py" ]; then
    if command -v python3 &>/dev/null; then
        if python3 tests/test_fixtures.py; then
            echo "  ✓ Fixture tests passed"
        else
            echo "  ✗ Fixture tests FAILED"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo "  ⚠ python3 not found — skipping tests"
        WARNINGS=$((WARNINGS + 1))
    fi
else
    echo "  ⚠ No test_fixtures.py found — skipping"
    WARNINGS=$((WARNINGS + 1))
fi
echo ""

# --- 5. Run E2E tests if available ---
if [ -f "tests/test_e2e.py" ]; then
    echo "▶ Running E2E enforcement tests..."
    if python3 tests/test_e2e.py; then
        echo "  ✓ E2E tests passed"
    else
        echo "  ✗ E2E tests FAILED"
        ERRORS=$((ERRORS + 1))
    fi
    echo ""
fi

# --- 6. Python-specific checks ---
if [ "$PROJECT_TYPE" = "python" ]; then
    echo "▶ Python syntax check..."
    SYNTAX_ERRORS=0
    for pyfile in $(find . -name "*.py" -not -path "./.venv/*" -not -path "./__pycache__/*"); do
        if ! python3 -c "import ast; ast.parse(open('$pyfile').read())" 2>/dev/null; then
            echo "  ✗ Syntax error in $pyfile"
            SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
        fi
    done
    if [ $SYNTAX_ERRORS -eq 0 ]; then
        echo "  ✓ All Python files parse cleanly"
    else
        ERRORS=$((ERRORS + SYNTAX_ERRORS))
    fi
    echo ""
fi

# --- Summary ---
echo "═══════════════════════════════════════════════════"
if [ $ERRORS -gt 0 ]; then
    echo "  RESULT: FAIL — $ERRORS error(s), $WARNINGS warning(s)"
    echo "═══════════════════════════════════════════════════"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo "  RESULT: PASS with $WARNINGS warning(s)"
    echo "═══════════════════════════════════════════════════"
    exit 0
else
    echo "  RESULT: PASS — all checks green"
    echo "═══════════════════════════════════════════════════"
    exit 0
fi
