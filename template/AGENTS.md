# {{PROJECT_NAME}}

{{PROJECT_PURPOSE}}

## Startup Workflow

1. Confirm working directory is the project root
2. Read this file for project rules and boundaries
3. Run `./init.sh` — must exit 0 before proceeding
4. Read `feature_list.json` — identify the ACTIVE phase
5. Read `progress.md` — understand current state and decisions

## Working Rules

- **WIP=1** — One task at a time. Finish or park before starting another.
- **Verify before claiming done** — Run the phase's verification command. Exit 0 = done.
- **Update progress.md** — Record what was done, decisions, and next steps before session end.
- **Stay in scope** — Only work within the active phase.
- **Leave clean state** — No temp files, no broken tests, no uncommitted debug code.

## Governance Boundaries

{{DENY_LIST_SUMMARY}}

Three enforcement gates fire on every tool call (mechanical, not advisory):
1. **Deny-list** — Hard-blocked patterns → `governance/deny-list.json`
2. **Phase-gate** — Tools locked until prerequisites pass → `tools/mcp-allowlist.json`
3. **Egress** — Outbound network default-deny → `tools/mcp-allowlist.json` egress_hosts

Enforcement mechanism: `governance/permission.py` (CLI mode, exit 0 = allow, exit 2 = block).

## Verification Commands

```bash
{{PRIMARY_VERIFICATION_COMMAND}}
```

## End of Session

1. Update `progress.md` with current state and decisions
2. Run `./init.sh` — confirm clean state
3. If phase complete: report "Phase X passes. Requesting sign-off." (do NOT self-transition)
4. If ending mid-task: fill the Session Handoff section in `progress.md`

## Escalation

- **Scope ambiguity:** Re-read `feature_list.json` + `context/` docs
- **Tool not available:** Check `tools/mcp-allowlist.json` — may be phase-gated
- **Repeated failures (3+):** Update progress.md, flag for human review
- **Permission denied:** Do not retry. Note in progress.md and move on.
- {{DOMAIN_ESCALATION_RULES}}

## Domain Context

See `context/` for domain-specific knowledge:
- [context/README.md](context/README.md) — What belongs here
- {{DOMAIN_CONTEXT_LINKS}}
