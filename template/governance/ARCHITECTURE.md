# Governance Module

Four-gate permission enforcement engine. Sits OUTSIDE the model — the model cannot see, edit, or bypass this code. It also protects itself: Gate 1a refuses writes to `permission.py` and the policy files (control S2.4).

## Responsibilities

- Evaluate tool calls against policy (protected paths, deny-list, phase-gate, egress)
- Fail-closed: unknown tools, missing phases, unlisted hosts → all denied
- Fail-closed on policy too: a missing or unparseable policy file raises `PolicyError`, which CLI mode turns into exit 2
- Dual interface: CLI (for hooks) + Python import (for tests)
- Serve **both** enforcement layers from one implementation: the CLI path for a Claude Code / Kiro session, and `runtime_dispatcher.py` for a deployed application that emits no hook events

## Files

| File | Role | Modify? |
|------|------|---------|
| `permission.py` | Enforcement mechanism — four gates in fixed order | **Never** per project |
| `runtime_dispatcher.py` | Enforcement mechanism — in-process chokepoint for a deployed app; gates ② ③ ④ by importing `permission.py` and `Security-kit/runtime_screen.py`. Holds no policy and no patterns of its own | **Never** per project |
| `deny-list.json` | Policy — `patterns` (substring blocks) + `protected_paths` (write targets, additive only) | **Always** fill per domain |
| `mcp-allowlist.json` | Policy — registered tools, `signed_off_phases`, egress hosts. Read by both the CLI path and the dispatcher | **Always** fill per domain |

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

**Deployed runtime (the application you ship — no hooks exist there):**
```python
from runtime_dispatcher import RuntimeDispatcher

dispatcher = RuntimeDispatcher({"fetch_article": fetch_article})
result = dispatcher.execute("fetch_article", {"url": "https://..."})
# Raises PermissionError if gate ② refuses — the tool is never called.
# The result is screened at ④ before it is returned.
```

## Constraints

- MUST NOT import external packages (stdlib only)
- MUST NOT be modified per project — all customisation goes into the JSON policy files
- Gate evaluation order is fixed: protected paths → deny-list → phase-gate → egress
- First denial terminates evaluation (no subsequent gates checked)
- `BUILTIN_PROTECTED_PATHS` is enforced unconditionally — the `protected_paths` policy key may only ADD to it, never shrink it, so emptying or deleting the policy file unprotects nothing. `runtime_dispatcher.py` is one of those built-in paths
- `runtime_dispatcher.py` MUST NOT re-implement a gate or hold a copy of a pattern. It exists to *call* `permission.py`; a second implementation is a second thing to drift
- Nothing here can force a deployed application to route through the dispatcher. That residual is `SEC-RUNTIME-GAP-001` (`Security-kit/SECURITY.md` S1.6), not a bug in this module
