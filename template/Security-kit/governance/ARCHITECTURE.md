# Governance Module

Three-gate permission enforcement engine. Sits OUTSIDE the model — the model cannot see, edit, or bypass this code.

## Responsibilities

- Evaluate tool calls against policy (deny-list, phase-gate, egress)
- Fail-closed: unknown tools, missing phases, unlisted hosts → all denied
- Dual interface: CLI (for hooks) + Python import (for tests)

## Files

| File | Role | Modify? |
|------|------|---------|
| `permission.py` | Enforcement mechanism — three gates in fixed order | **Never** per project |
| `deny-list.json` | Policy — substring patterns that cause immediate block | **Always** fill per domain |

## Interface

**CLI mode (production — called by `.claude/settings.json` hooks):**
```bash
echo '{"tool_name": "bash", "tool_input": {"command": "rm -rf /"}}' | python3 governance/permission.py
# Exit 0 = allow, Exit 2 = BLOCK (prints reason to stdout)
```

**Python import (tests + demo):**
```python
from governance.permission import make_permission_check, check_deny_list, check_phase_gate, check_egress
```

## Constraints

- MUST NOT import external packages (stdlib only)
- MUST NOT be modified per project — all customisation goes into the JSON policy files
- Gate evaluation order is fixed: deny-list → phase-gate → egress
- First denial terminates evaluation (no subsequent gates checked)
