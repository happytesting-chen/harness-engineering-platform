#!/usr/bin/env bash
# install.sh — assemble a template build.
#
# Default: full build (security kit intact) — this is a no-op that just confirms layout.
# --no-security: produce a build with the security layer removed, per security/SECURITY-MANIFEST.md
#                (Tier 1 deleted, Tier 3 security parts neutralized in place).
#
# Safety: refuses to run on the canonical template unless --force; intended to run on a
# COPY. Use --dry-run to preview. See security/SECURITY-MANIFEST.md for the full rationale.
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
echo "  Removes the security layer per security/SECURITY-MANIFEST.md"
echo "═══════════════════════════════════════════════════"

# Guard: don't nuke the canonical template by accident.
if [ -d "../.git" ] && [ "$FORCE" -eq 0 ] && [ "$DRY_RUN" -eq 0 ]; then
  echo "✗ Refusing to strip security inside a git repo without --force."
  echo "  Run on a COPY (cp -r template/ my-agent/), or pass --force, or --dry-run."
  exit 1
fi

# Tier 1 — delete pure-security paths.
# Remove whole directories (Security-kit/, kiro/hooks/) rather than files piecemeal, so
# no empty security dir is left behind to trip init.sh's integrity block (which is guarded
# by `if [ -d "Security-kit/governance" ]`).
TIER1=(
  "Security-kit" "Harness-Best-Practice/observability/audit_hook.py"
  "kiro/steering/security.md" "kiro/steering/security-review.md" "kiro/hooks"
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
if [ -f "init.sh" ]; then
  run "sed -i.bak 's#\"Security-kit/governance/deny-list.json\" \"Security-kit/governance/mcp-allowlist.json\"##' init.sh && rm -f init.sh.bak"
  echo "  ~ init.sh (removed governance JSON from REQUIRED_FILES; integrity block auto-skips)"
fi

echo ""
echo "✓ no-security build ready. Note: this build has NO mechanical enforcement."
echo "  Record this deliberate choice in progress.md / control-matrix decisions."
echo "  Run ./init.sh to confirm the remaining (non-security) checks pass."
