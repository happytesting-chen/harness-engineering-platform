#!/usr/bin/env bash
# install.sh — assemble a template build.
#
# Default: full build (security kit intact) — this is a no-op that just confirms layout.
# --no-security: produce a build with the security layer removed, per Security-kit/SECURITY-MANIFEST.md
#                (Tier 1 deleted, Tier 3 security parts neutralized in place).
#
# Safety: refuses to run on the canonical template unless --force; intended to run on a
# COPY. Use --dry-run to preview. See Security-kit/SECURITY-MANIFEST.md for the full rationale.
#
# Usage:
#   cp -r template/ my-agent/ && cd my-agent/
#   ./install.sh                 # full build (default)
#   ./install.sh --no-security --dry-run   # preview what would be removed
#   ./install.sh --no-security             # strip the security layer

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="full"
DRY_RUN=0
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --no-security) MODE="no-security" ;;
    --dry-run)     DRY_RUN=1 ;;
    --force)       FORCE=1 ;;
    --help|-h)
      grep '^#' "$0" | sed 's/^# \{0,1\}//' | head -20; exit 0 ;;
    *) echo "unknown arg: $arg (see --help)"; exit 1 ;;
  esac
done

run() {  # echo in dry-run, execute otherwise
  if [ "$DRY_RUN" -eq 1 ]; then echo "  [dry-run] $*"; else eval "$*"; fi
}

if [ "$MODE" = "full" ]; then
  echo "▶ Full build (security kit intact). Nothing to assemble — run ./init.sh next."
  exit 0
fi

# --- no-security build ---
echo "═══════════════════════════════════════════════════"
[ "$DRY_RUN" -eq 1 ] && LABEL="(dry-run)" || LABEL=""
echo "  install.sh --no-security  $LABEL"
echo "  Removes the security layer per Security-kit/SECURITY-MANIFEST.md"
echo "═══════════════════════════════════════════════════"

# Guard: don't nuke the canonical template by accident.
if [ -d "../.git" ] && [ "$FORCE" -eq 0 ] && [ "$DRY_RUN" -eq 0 ]; then
  echo "✗ Refusing to strip security inside a git repo without --force."
  echo "  Run on a COPY (cp -r template/ my-agent/), or pass --force, or --dry-run."
  exit 1
fi

# Tier 1 — delete pure-security paths.
# Remove whole directories (governance/, Security-kit/, tests/, kiro/hooks/) rather than
# files piecemeal, so no empty security dir is left behind to trip init.sh's integrity
# block (which is guarded by `if [ -d "governance" ]`).
TIER1=(
  "governance" "Security-kit" "tests"
  "Harness-Best-Practice/observability/audit_hook.py"
  "kiro/steering/security.md" "kiro/steering/security-review.md" "kiro/hooks"
  "kiro/steering/security-tailor.md"
  ".claude/commands/security-tailor.md"
  "docs/superpowers" "progress.md"
)
echo "▶ Deleting Tier 1 (pure security)..."
for p in "${TIER1[@]}"; do
  [ -e "$p" ] && run "rm -rf '$p'" && echo "  - $p" || true
done

# Tier 3 — neutralize security parts in place
echo "▶ Neutralizing Tier 3 (wired) security parts..."

# .claude/settings.json → keep only Stop hooks
if [ -f ".claude/settings.json" ]; then
  run "python3 - <<'PY'
import json
p='.claude/settings.json'; d=json.load(open(p))
d.get('hooks',{}).pop('PreToolUse',None)
d.get('hooks',{}).pop('PostToolUse',None)
json.dump(d, open(p,'w'), indent=2)
PY"
  echo "  ~ .claude/settings.json (dropped PreToolUse/PostToolUse hooks)"
fi

# init.sh → drop REQUIRED_FILES governance entries (integrity block self-skips when governance/ is gone)
#          → also drop the dead /security-tailor error-message line (guard file is gone)
if [ -f "init.sh" ]; then
  run "sed -i.bak 's#\"governance/deny-list.json\" \"governance/mcp-allowlist.json\"##' init.sh && rm -f init.sh.bak"
  run "sed -i.bak '/run \/security-tailor and fill verifications/d' init.sh && rm -f init.sh.bak"
  echo "  ~ init.sh (removed governance JSON from REQUIRED_FILES; stripped dead /security-tailor error line)"
fi

# CLAUDE.md → strip the layer-D comment block AND the import (its target is deleted with Security-kit/)
if [ -f "CLAUDE.md" ]; then
  run "python3 - <<'PY'
p = 'CLAUDE.md'
lines = open(p).readlines()
out = []
i = 0
while i < len(lines):
    line = lines[i]
    if '@Security-kit/active-controls.md' in line:
        i += 1
        continue
    stripped = line.strip()
    if stripped.startswith('<!--'):
        block = [line]
        j = i
        if '-->' not in line:
            j = i + 1
            while j < len(lines) and '-->' not in lines[j]:
                block.append(lines[j])
                j += 1
            if j < len(lines):
                block.append(lines[j])
        block_text = ''.join(block)
        if any(kw in block_text for kw in ['layer D', 'security-tailor', 'active-controls']):
            i = j + 1
            continue
        else:
            out.extend(block)
            i = j + 1
            continue
    out.append(line)
    i += 1
open(p, 'w').writelines(out)
PY"
  echo "  ~ CLAUDE.md (removed layer-D comment + @Security-kit/active-controls.md import)"
fi

# .claude/commands/init-project.md → remove Step 2b (/security-tailor invocation)
if [ -f ".claude/commands/init-project.md" ]; then
  run "python3 - <<'PY'
p = '.claude/commands/init-project.md'
lines = open(p).readlines()
out = []
i = 0
while i < len(lines):
    if lines[i].startswith('## Step 2b'):
        while i < len(lines) and not lines[i].startswith('## Step 3'):
            i += 1
    else:
        out.append(lines[i])
        i += 1
open(p, 'w').writelines(out)
PY"
  echo "  ~ .claude/commands/init-project.md (removed /security-tailor reference)"
fi

# .claude/commands/session-cycle.md → remove step 11b (/security-tailor re-run)
if [ -f ".claude/commands/session-cycle.md" ]; then
  run "python3 - <<'PY'
p = '.claude/commands/session-cycle.md'
lines = open(p).readlines()
out = []
i = 0
while i < len(lines):
    if lines[i].startswith('11b.'):
        while i < len(lines) and not lines[i].startswith('12.'):
            i += 1
    else:
        out.append(lines[i])
        i += 1
open(p, 'w').writelines(out)
PY"
  echo "  ~ .claude/commands/session-cycle.md (removed /security-tailor reference)"
fi

# kiro/steering/session-cycle.md → remove step 11b (/security-tailor re-run)
if [ -f "kiro/steering/session-cycle.md" ]; then
  run "python3 - <<'PY'
p = 'kiro/steering/session-cycle.md'
lines = open(p).readlines()
out = []
i = 0
while i < len(lines):
    if lines[i].startswith('11b.'):
        while i < len(lines) and not lines[i].startswith('12.'):
            i += 1
    else:
        out.append(lines[i])
        i += 1
open(p, 'w').writelines(out)
PY"
  echo "  ~ kiro/steering/session-cycle.md (removed /security-tailor reference)"
fi

echo ""
echo "✓ no-security build ready. Note: this build has NO mechanical enforcement."
echo "  Record this deliberate choice in progress.md / control-matrix decisions."
echo "  Run ./init.sh to confirm the remaining (non-security) checks pass."
