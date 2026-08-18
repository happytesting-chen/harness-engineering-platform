# AI News Runtime Security Demo

Build a small AI + cybersecurity news application that proves the harness security controls remain active in the deployed runtime, not only during development.

<!-- System identity (tech stack, architecture, hard constraints) lives in AGENTS.md
     (under Harness-Best-Practice/), the open standard other agents read. Import it so
     Claude loads it too, rather than duplicating it here. This CLAUDE.md adds the
     Claude-specific session workflow. Import path is relative to this file (root). -->
@Harness-Best-Practice/AGENTS.md
<!-- Tailored, product-specific security controls (layer D). Ships as a stub; /security-tailor
     regenerates it from coverage.json. Stripped by install.sh --no-security. -->
@Security-kit/active-controls.md

## Startup Workflow

1. Confirm working directory is the project root
2. Read this file for project rules and boundaries
3. Run `./init.sh` — must exit 0 before proceeding
4. Read `Harness-Best-Practice/feature_list.json` — identify the ACTIVE phase
5. Read `Harness-Best-Practice/progress.md` — understand current state and decisions
6. Read the project context files listed under **Domain Context** below before changing application code

## Working Rules

- **WIP=1** — One task at a time. Finish or park before starting another.
- **Verify before claiming done** — Run the phase's verification command. Exit 0 = done.
- **Update progress.md** — Record what was done, decisions, and next steps before session end.
- **Stay in scope** — Only work within the active phase.
- **Leave clean state** — No temp files, no broken tests, no uncommitted debug code.
- Do not redesign the generic harness while building the application. If a genuine reusable harness defect is discovered, document it separately before changing mechanism code.

## Governance Boundaries

The agent may use only tools and outbound destinations explicitly permitted by `governance/mcp-allowlist.json`. Protected harness/security mechanism files remain guarded by `governance/permission.py` and deny-list policy.

Four enforcement gates fire on every gated tool call, in this order (mechanical, not advisory).
First denial wins; the gate fails closed.
1. **Protected paths** — the mechanism's own files are unwritable → `permission.py` `BUILTIN_PROTECTED_PATHS`
2. **Deny-list** — Hard-blocked patterns → `governance/deny-list.json`
3. **Phase-gate** — Tools locked until prerequisites pass → `governance/mcp-allowlist.json`
4. **Egress** — Outbound network default-deny → `governance/mcp-allowlist.json` egress_hosts

Gate 1 runs **first** and enforces S2.4 — the agent cannot edit its own policy/mechanism.

## Verification Commands

```bash
python3 -m pytest -q
```

## End of Session

1. Update `Harness-Best-Practice/progress.md` with current state and decisions
2. Run `./init.sh` — confirm clean state
3. If phase complete: report "Phase X passes. Requesting sign-off." (do NOT self-transition)
4. If ending mid-task: fill the Session Handoff section in `Harness-Best-Practice/progress.md`

## Escalation

- **Scope ambiguity:** Re-read `Harness-Best-Practice/feature_list.json` + `Context/` docs
- **Tool not available:** Check `governance/mcp-allowlist.json` — may be phase-gated or intentionally excluded
- **Repeated failures (3+):** Update `Harness-Best-Practice/progress.md`, flag for human review
- **Permission denied:** Do not retry around the control. Record the denial and investigate policy/implementation.
- **External source requires an unapproved host:** do not automatically add it; surface the required host for explicit review.

## Reference

- [BEST-PRACTICES.md](Harness-Best-Practice/BEST-PRACTICES.md) — Harness engineering principles

## Domain Context

Read these project-specific files before implementing the application:

- [Context/README.md](Context/README.md) — what belongs in project context
- [Context/ai-stack.md](Context/ai-stack.md) — Strands, Claude, Streamlit, runtime tools and security path
- [Context/deployment.md](Context/deployment.md) — local runtime, secrets, egress and data boundaries
- [Context/target-scope.md](Context/target-scope.md) — in/out of scope and E01–E06 runtime-security acceptance criteria
