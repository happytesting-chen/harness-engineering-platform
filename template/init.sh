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
REQUIRED_FILES=("CLAUDE.md" "Harness-Best-Practice/AGENTS.md" "Harness-Best-Practice/feature_list.json" "governance/deny-list.json" "governance/mcp-allowlist.json")
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
if [ -f "Harness-Best-Practice/progress.md" ]; then
    PROGRESS_MTIME=$(stat -f %m "Harness-Best-Practice/progress.md" 2>/dev/null || stat -c %Y "Harness-Best-Practice/progress.md" 2>/dev/null || echo "0")
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

# --- 5b. Security-kit integrity gate ---
# A governed-agent template must not silently pass with its enforcement removed or
# unwired. This gate fails if the mechanism is absent, the hook is not wired, or the
# hook-integration proof does not pass. Skipped only if this copy intentionally ships
# no governance/ at all (a deliberately ungoverned project).
if [ -d "governance" ]; then
    echo "▶ Security-kit integrity..."
    # (a) enforcement engine present
    if [ -f "governance/permission.py" ]; then
        echo "  ✓ enforcement engine present (governance/permission.py)"
    else
        echo "  ✗ governance/ exists but permission.py is MISSING — enforcement gutted"
        ERRORS=$((ERRORS + 1))
    fi
    # (b) hook actually wired to the engine in .claude/settings.json
    if [ -f ".claude/settings.json" ] && grep -q "governance/permission.py" .claude/settings.json; then
        echo "  ✓ permission gate wired in .claude/settings.json"
    else
        echo "  ✗ .claude/settings.json does NOT wire governance/permission.py — gate inert"
        ERRORS=$((ERRORS + 1))
    fi
    # (c) hook-integration proof passes (drives the real hook scripts via stdin)
    if [ -f "tests/test_hooks.py" ]; then
        if python3 tests/test_hooks.py >/dev/null 2>&1; then
            echo "  ✓ hook-integration tests passed (tests/test_hooks.py)"
        else
            echo "  ✗ hook-integration tests FAILED — enforcement path broken"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo "  ⚠ no tests/test_hooks.py — hook wiring is unproven"
        WARNINGS=$((WARNINGS + 1))
    fi
    # (d) data-plane content-trust proof (untrusted-content boundary)
    if [ -f "Security-kit/content_trust.py" ] && [ -f "tests/test_content_trust.py" ]; then
        if python3 tests/test_content_trust.py >/dev/null 2>&1; then
            echo "  ✓ content-trust tests passed (tests/test_content_trust.py)"
        else
            echo "  ✗ content-trust tests FAILED — data-plane boundary broken"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo "  ⚠ no content-trust primitive — untrusted-content boundary is app-only"
        WARNINGS=$((WARNINGS + 1))
    fi
    # (e) hook-path integrity: every hook script wired in settings.json must resolve on
    # disk. A missing path makes python3 exit 2 — indistinguishable from a real policy
    # BLOCK — so a wrong path silently fail-closes EVERY tool. This check catches that
    # config error before it bricks a session (distinct from a deny decision).
    if [ -f ".claude/settings.json" ]; then
        MISSING_HOOKS=$(python3 -c '
import json, re, os, sys
try:
    cfg = json.load(open(".claude/settings.json"))
except Exception as e:
    print("UNPARSEABLE:" + str(e)); sys.exit(0)
blob = json.dumps(cfg)
seen = set()
for raw in re.findall(r"\$CLAUDE_PROJECT_DIR/(\S+?\.py)", blob):
    p = raw.strip(chr(34) + chr(39))
    if p not in seen:
        seen.add(p)
        if not os.path.isfile(p):
            print(p)
')
        if [ -z "$MISSING_HOOKS" ]; then
            echo "  ✓ all wired hook paths resolve on disk"
        else
            echo "  ✗ GATE MISCONFIGURED — settings.json wires hook script(s) that do NOT exist:"
            echo "$MISSING_HOOKS" | sed 's/^/        (config error, not a policy block) /'
            ERRORS=$((ERRORS + 1))
        fi
    fi
    # (f) coverage-checker ground-truth tests (named explicitly — init.sh has no glob runner)
    if [ -f "tests/test_coverage.py" ]; then
        if python3 tests/test_coverage.py >/dev/null 2>&1; then
            echo "  ✓ coverage-checker tests passed (tests/test_coverage.py)"
        else
            echo "  ✗ coverage-checker tests FAILED (tests/test_coverage.py)"
            ERRORS=$((ERRORS + 1))
        fi
    fi
    # (g) selection-scorer math tests
    if [ -f "tests/test_eval_selection.py" ]; then
        if python3 tests/test_eval_selection.py >/dev/null 2>&1; then
            echo "  ✓ selection-scorer tests passed (tests/test_eval_selection.py)"
        else
            echo "  ✗ selection-scorer tests FAILED (tests/test_eval_selection.py)"
            ERRORS=$((ERRORS + 1))
        fi
    fi
    # (h) coverage gate: applicable controls must be mapped to a verification
    if [ -f "Security-kit/check_coverage.py" ]; then
        if python3 Security-kit/check_coverage.py; then
            echo "  ✓ security coverage complete (Security-kit/check_coverage.py)"
        else
            echo "  ✗ security coverage incomplete — run /security-tailor and fill verifications"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo "  ⚠ no check_coverage.py — control coverage is unproven"
        WARNINGS=$((WARNINGS + 1))
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

# --- 6b. Evaluation primitive (optional; measures task quality) ---
if [ -f "evaluation/eval.py" ]; then
    echo "▶ Evaluation — quantifying reference target..."
    if python3 evaluation/eval.py >/dev/null 2>&1; then
        echo "  ✓ eval.py runs; reference target at 100% accuracy + reproducibility"
    else
        echo "  ✗ eval.py reference target regressed (accuracy/reproducibility < 100%)"
        ERRORS=$((ERRORS + 1))
    fi
    echo ""
fi

# --- 7. Fresh Session Test (Lecture 03) ---
echo "▶ Fresh Session Test — can a new session answer the 5 questions?"
FST_PASS=0
FST_FAIL=0

# Q1: What is this? (AGENTS.md exists and has content beyond placeholders)
if [ -f "Harness-Best-Practice/AGENTS.md" ] && [ "$(wc -l < Harness-Best-Practice/AGENTS.md)" -gt 5 ]; then
    echo "  ✓ Q1 (What is this?) — AGENTS.md present"
    FST_PASS=$((FST_PASS + 1))
else
    echo "  ✗ Q1 (What is this?) — AGENTS.md missing or empty"
    FST_FAIL=$((FST_FAIL + 1))
fi

# Q2: How do I run it? (init.sh exists and is executable)
if [ -x "init.sh" ]; then
    echo "  ✓ Q2 (How to run?) — init.sh present and executable"
    FST_PASS=$((FST_PASS + 1))
else
    echo "  ✗ Q2 (How to run?) — init.sh missing or not executable"
    FST_FAIL=$((FST_FAIL + 1))
fi

# Q3: How do I verify it? (feature_list.json has at least one verification command that
#     is neither a {{placeholder}} nor a flagged NEEDS-CONFIRMATION / TODO / TBD value)
if [ -f "Harness-Best-Practice/feature_list.json" ]; then
    HAS_VERIFY=$(grep -c '"verification"' Harness-Best-Practice/feature_list.json 2>/dev/null || true)
    PLACEHOLDER_VERIFY=$(grep -c '{{.*VERIFY' Harness-Best-Practice/feature_list.json 2>/dev/null || true)
    # A verification value that is present but flagged as unconfirmed is NOT a real
    # verification command — treat NEEDS-CONFIRMATION / TODO / TBD as unfilled.
    FLAGGED_VERIFY=$(grep '"verification"' Harness-Best-Practice/feature_list.json 2>/dev/null \
        | grep -c -E 'NEEDS-CONFIRMATION|TODO|TBD' || true)
    HAS_VERIFY=${HAS_VERIFY:-0}
    PLACEHOLDER_VERIFY=${PLACEHOLDER_VERIFY:-0}
    FLAGGED_VERIFY=${FLAGGED_VERIFY:-0}
    if [ "$HAS_VERIFY" -gt 0 ] && [ "$PLACEHOLDER_VERIFY" -eq 0 ] && [ "$FLAGGED_VERIFY" -eq 0 ]; then
        echo "  ✓ Q3 (How to verify?) — feature_list.json has verification commands"
        FST_PASS=$((FST_PASS + 1))
    elif [ "$FLAGGED_VERIFY" -gt 0 ]; then
        echo "  ⚠ Q3 (How to verify?) — verification commands flagged NEEDS-CONFIRMATION/TODO/TBD"
        FST_FAIL=$((FST_FAIL + 1))
    else
        echo "  ⚠ Q3 (How to verify?) — verification commands are still placeholders"
        FST_FAIL=$((FST_FAIL + 1))
    fi
else
    echo "  ✗ Q3 (How to verify?) — feature_list.json missing"
    FST_FAIL=$((FST_FAIL + 1))
fi

# Q4: What's done? (feature_list.json is readable + progress.md exists)
if [ -f "Harness-Best-Practice/feature_list.json" ] && [ -f "Harness-Best-Practice/progress.md" ]; then
    echo "  ✓ Q4 (What's done?) — feature_list.json + progress.md present"
    FST_PASS=$((FST_PASS + 1))
else
    echo "  ✗ Q4 (What's done?) — feature_list.json or progress.md missing"
    FST_FAIL=$((FST_FAIL + 1))
fi

# Q5: What's next? (feature_list.json has at least one not-started item)
if [ -f "Harness-Best-Practice/feature_list.json" ]; then
    HAS_NEXT=$(grep -c '"not-started"' Harness-Best-Practice/feature_list.json 2>/dev/null || echo "0")
    HAS_ACTIVE=$(grep -c '"active"' Harness-Best-Practice/feature_list.json 2>/dev/null || echo "0")
    if [ "$HAS_NEXT" -gt 0 ] || [ "$HAS_ACTIVE" -gt 0 ]; then
        echo "  ✓ Q5 (What's next?) — feature_list.json has pending work"
        FST_PASS=$((FST_PASS + 1))
    else
        echo "  ✓ Q5 (What's next?) — all features passing (project complete)"
        FST_PASS=$((FST_PASS + 1))
    fi
else
    echo "  ✗ Q5 (What's next?) — feature_list.json missing"
    FST_FAIL=$((FST_FAIL + 1))
fi

echo "  ─── Fresh Session Test: $FST_PASS/5 passed ───"
if [ $FST_FAIL -gt 0 ]; then
    WARNINGS=$((WARNINGS + FST_FAIL))
fi
echo ""

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
