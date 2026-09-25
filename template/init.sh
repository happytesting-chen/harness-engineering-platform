#!/usr/bin/env bash
# init.sh — Project verification script
# Exit 0 = healthy. Non-zero = issues found.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
ERRORS=0
WARNINGS=0

echo "═══════════════════════════════════════════════════"
echo "  Harness Engineering Platform — init.sh"
echo "═══════════════════════════════════════════════════"

# Required project and security files.
REQUIRED_FILES=(
  "CLAUDE.md"
  "AGENTS.md"
  "Harness-Best-Practice/feature_list.json"
  "security/shared/permission.py"
  "security/shared/deny-list.json"
  "security/shared/mcp-allowlist.json"
  "security/shared/content_trust.py"
  "security/shared/result_screen.py"
  "security/buildtime/prompt_screen.py"
  "security/buildtime/secret_scan.py"
  "security/runtime/runtime_dispatcher.py"
  "security/runtime/runtime_screen.py"
)

echo "▶ Checking required files and placeholders..."
for f in "${REQUIRED_FILES[@]}"; do
  if [ ! -f "$f" ]; then
    echo "  ✗ MISSING: $f"
    ERRORS=$((ERRORS + 1))
    continue
  fi
  if grep -q '{{[^}]*}}' "$f" 2>/dev/null; then
    echo "  ✗ UNFILLED placeholders: $f"
    ERRORS=$((ERRORS + 1))
  else
    echo "  ✓ $f"
  fi
done

# Check mcp-allowlist.json for unfilled tool placeholders
if grep -q '_PLACEHOLDER_REPLACE_ME\|{{GATED_TOOL}}' security/shared/mcp-allowlist.json 2>/dev/null; then
  echo "  ✗ mcp-allowlist.json contains placeholder tool — developer must replace with a real tool name"
  ERRORS=$((ERRORS + 1))
fi

# Claude hook wiring must use only the migrated security paths.
echo "▶ Checking Claude security hook wiring..."
if [ -f ".claude/settings.json" ]; then
  for p in \
    'security/buildtime/prompt_screen.py' \
    'security/shared/permission.py' \
    'security/buildtime/secret_scan.py' \
    'security/shared/result_screen.py'; do
    if grep -q "$p" .claude/settings.json; then
      echo "  ✓ wired: $p"
    else
      echo "  ✗ hook not wired: $p"
      ERRORS=$((ERRORS + 1))
    fi
  done
  if grep -Eq 'Security-kit/|governance/' .claude/settings.json; then
    echo "  ✗ retired security path remains in .claude/settings.json"
    ERRORS=$((ERRORS + 1))
  fi
else
  echo "  ✗ .claude/settings.json missing"
  ERRORS=$((ERRORS + 1))
fi

# Every command-style hook path should resolve on disk.
if command -v python3 >/dev/null 2>&1 && [ -f ".claude/settings.json" ]; then
  if ! python3 - <<'PY'
import json, os, re, sys
cfg = json.load(open('.claude/settings.json'))
missing = []
for groups in cfg.get('hooks', {}).values():
    for group in groups:
        for hook in group.get('hooks', []):
            cmd = hook.get('command', '')
            for rel in re.findall(r'\$CLAUDE_PROJECT_DIR/([^" ]+)', cmd):
                if not os.path.exists(rel):
                    missing.append(rel)
if missing:
    print('missing hook paths: ' + ', '.join(sorted(set(missing))))
    sys.exit(1)
PY
  then
    echo "  ✗ one or more hook paths do not resolve"
    ERRORS=$((ERRORS + 1))
  else
    echo "  ✓ hook paths resolve"
  fi
fi

# Warn if any phase is "passing" in feature_list.json but not in signed_off_phases
if [ -f "Harness-Best-Practice/feature_list.json" ] && [ -f "security/shared/mcp-allowlist.json" ]; then
  python3 - <<'PYCHECK'
import json, sys
from pathlib import Path
fl = json.loads(Path("Harness-Best-Practice/feature_list.json").read_text())
al = json.loads(Path("security/shared/mcp-allowlist.json").read_text())
signed = set(al.get("signed_off_phases", []))
for phase in fl.get("features", []):
    if phase.get("status") == "passing" and phase["id"] not in signed:
        print(f"  ⚠ Phase {phase['id']} is 'passing' but not signed off — run: python3 security/shared/signoff.py {phase['id']}")
PYCHECK
fi

# Security coverage checker owns its own shared-layer-relative artifacts.
echo "▶ Checking security coverage..."
if [ -f "security/shared/check_coverage.py" ]; then
  if python3 security/shared/check_coverage.py; then
    echo "  ✓ security coverage check passed"
  else
    echo "  ✗ security coverage check failed"
    ERRORS=$((ERRORS + 1))
  fi
else
  echo "  ✗ security/shared/check_coverage.py missing"
  ERRORS=$((ERRORS + 1))
fi

# Run the test suite through pytest so tests/conftest.py installs the migrated import paths.
echo "▶ Running tests..."
if command -v python3 >/dev/null 2>&1 && python3 -m pytest --version >/dev/null 2>&1; then
  if python3 -m pytest tests -q; then
    echo "  ✓ tests passed"
  else
    echo "  ✗ tests failed"
    ERRORS=$((ERRORS + 1))
  fi
else
  echo "  ⚠ pytest unavailable — tests not run"
  WARNINGS=$((WARNINGS + 1))
fi

echo ""
echo "═══════════════════════════════════════════════════"
if [ "$ERRORS" -eq 0 ]; then
  echo "RESULT: PASS — 0 error(s), $WARNINGS warning(s)"
  exit 0
fi
echo "RESULT: FAIL — $ERRORS error(s), $WARNINGS warning(s)"
exit 1
