# Governance Module

Four-gate permission enforcement engine. Sits OUTSIDE the model — the model cannot see, edit, or bypass this code. It also protects itself: Gate 1a refuses writes to `permission.py` and the policy files (control S2.4).

## Responsibilities

- Evaluate tool calls against policy (protected paths, deny-list, phase-gate, egress)
- Fail-closed: unknown tools, missing phases, unlisted hosts → all denied
- Fail-closed on policy too: a missing or unparseable policy file raises `PolicyError`, which CLI mode turns into exit 2
- Dual interface: CLI (for hooks) + Python import (for tests)

## Files

| File | Role | Modify? |
|------|------|---------|
| `permission.py` | Enforcement mechanism — four gates in fixed order | **Never** per project |
| `deny-list.json` | Policy — `patterns` (substring blocks) + `protected_paths` (write targets, additive only) | **Always** fill per domain |

## Interface

**CLI mode (production — called by `.claude/settings.json` hooks):**
```bash
echo '{"tool_name": "bash", "tool_input": {"command": "rm -rf /"}}' | python3 governance/permission.py
# Exit 0 = allow, Exit 2 = BLOCK (prints reason to stdout)
```

**Python import (tests + demo):**
```python
from governance.permission import (
    make_permission_check,
    check_protected_paths,
    check_deny_list,
    check_phase_gate,
    check_egress,
)
```

## Constraints

- MUST NOT import external packages (stdlib only)
- MUST NOT be modified per project — all customisation goes into the JSON policy files
- Gate evaluation order is fixed: protected paths → deny-list → phase-gate → egress
- First denial terminates evaluation (no subsequent gates checked)
- `BUILTIN_PROTECTED_PATHS` is enforced unconditionally — the `protected_paths` policy key may only ADD to it, never shrink it, so emptying or deleting the policy file unprotects nothing
