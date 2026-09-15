#!/usr/bin/env bash
# install.sh — assemble a template build.
#
# Default: full build (security layer intact).
# --no-security: produce a build with the security layer removed, per
#                security/shared/SECURITY-MANIFEST.md.
#
# Safety: refuses to run on the canonical template unless --force; intended to run on a COPY.
# Use --dry-run to preview.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="full"; DRY_RUN=0; FORCE=0
for arg in "$@"; do
  case "$arg" in
    --no-security) MODE="no-security" ;;
    --dry-run) DRY_RUN=1 ;;
    --force) FORCE=1 ;;
    --help|-h) grep '^#' "$0" | sed 's/^# \{0,1\}//' | head -20; exit 0 ;;
    *) echo "unknown arg: $arg (see --help)"; exit 1 ;;
  esac
done

run() { if [ "$DRY_RUN" -eq 1 ]; then echo "  [dry-run] $*"; else eval "$*"; fi; }

if [ "$MODE" = "full" ]; then
  echo "▶ Full build (security layer intact). Nothing to assemble — run ./init.sh next."
  exit 0
fi

echo "═══════════════════════════════════════════════════"
[ "$DRY_RUN" -eq 1 ] && LABEL="(dry-run)" || LABEL=""
echo "  install.sh --no-security  $LABEL"
echo "  Removes the security layer per security/shared/SECURITY-MANIFEST.md"
echo "═══════════════════════════════════════════════════"

if [ -d "../.git" ] && [ "$FORCE" -eq 0 ] && [ "$DRY_RUN" -eq 0 ]; then
  echo "✗ Refusing to strip security inside a git repo without --force."
  echo "  Run on a COPY, pass --force, or use --dry-run."
  exit 1
fi

# Pure-security paths. The migrated security/ tree owns build-time, shared-policy,
# and deployed-runtime security code.
TIER1=(
  "security" "tests"
  "Harness-Best-Practice/observability/audit_hook.py"
  "kiro/steering/security.md" "kiro/steering/security-review.md" "kiro/hooks"
  "kiro/steering/security-tailor.md" "kiro/steering/active-controls.md"
  ".claude/commands/security-tailor.md"
  "docs/superpowers" "progress.md"
)
echo "▶ Deleting Tier 1 (pure security)..."
for p in "${TIER1[@]}"; do
  [ -e "$p" ] && run "rm -rf '$p'" && echo "  - $p" || true
done

# Remove security hooks while retaining unrelated Stop hooks.
if [ -f ".claude/settings.json" ]; then
  run "python3 - <<'PY'
import json
p='.claude/settings.json'; d=json.load(open(p))
for key in ('PreToolUse','PostToolUse','UserPromptSubmit'):
    d.get('hooks',{}).pop(key,None)
json.dump(d, open(p,'w'), indent=2)
PY"
  echo "  ~ .claude/settings.json (dropped security hooks)"
fi

# Remove the active-controls import whose target was deleted with security/.
if [ -f "CLAUDE.md" ]; then
  run "python3 - <<'PY'
p='CLAUDE.md'; lines=open(p).readlines(); out=[]; i=0
while i < len(lines):
    line=lines[i]
    if '@security/shared/active-controls.md' in line:
        i += 1; continue
    if line.strip().startswith('<!--'):
        block=[line]; j=i
        if '-->' not in line:
            j=i+1
            while j < len(lines) and '-->' not in lines[j]: block.append(lines[j]); j+=1
            if j < len(lines): block.append(lines[j])
        if any(k in ''.join(block) for k in ('layer D','security-tailor','active-controls')):
            i=j+1; continue
        out.extend(block); i=j+1; continue
    out.append(line); i+=1
open(p,'w').writelines(out)
PY"
  echo "  ~ CLAUDE.md (removed active-controls import/comment)"
fi

# Remove security-tailoring workflow steps from host instructions.
for p in ".claude/commands/init-project.md" ".claude/commands/session-cycle.md" "kiro/steering/session-cycle.md"; do
  [ -f "$p" ] || continue
  run "python3 - '$p' <<'PY'
import sys
p=sys.argv[1]; lines=open(p).readlines(); out=[]; i=0
while i < len(lines):
    if lines[i].startswith('## Step 2b'):
        while i < len(lines) and not lines[i].startswith('## Step 3'): i+=1
        continue
    if lines[i].startswith('11b.'):
        while i < len(lines) and not lines[i].startswith('12.'): i+=1
        continue
    out.append(lines[i]); i+=1
open(p,'w').writelines(out)
PY"
  echo "  ~ $p (removed security-tailor workflow reference)"
done

echo ""
echo "✓ no-security build ready. Note: this build has NO mechanical security enforcement."
echo "  Run ./init.sh to confirm the remaining checks pass."
