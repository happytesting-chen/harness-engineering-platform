# {{PROJECT_NAME}}

{{PROJECT_PURPOSE}}

## Startup Workflow

1. Confirm working directory is the project root
2. Read this file (CLAUDE.md) for project rules and boundaries
3. Run `./init.sh` — confirm environment healthy (exit 0 required)
4. Read `feature_list.json` — identify the one ACTIVE phase
5. Read `progress.md` — understand current state, decisions, and blockers
6. Check recent commits for context on latest changes

## Working Rules

- **WIP=1** — Work on one task at a time. Finish or park before starting another.
- **Verify before claiming done** — Run the phase's verification command. Green = done.
- **Update progress.md** — Record what was done, decisions made, and next steps before session end.
- **Stay in scope** — Only work within the active phase. If a task touches a future phase, stop and note it.
- **Leave clean state** — No temp files, no broken tests, no uncommitted debug code.

## Governance Boundaries

{{DENY_LIST_SUMMARY}}

The permission gate enforces three controls automatically:
1. **Deny-list** — Hard-blocked patterns (see `governance/deny-list.json`)
2. **Phase-gate** — Tools locked until prerequisite phases pass (see `tools/mcp-allowlist.json`)
3. **Egress control** — Outbound network default-deny unless host is allowlisted

These are enforced mechanically — the model cannot bypass them.

## Required Artifacts

- `feature_list.json` — Phase status and verification commands
- `progress.md` — Session continuity record
- `observability/audit.log` — Append-only decision log (do not edit)

## Verification Commands

```bash
{{PRIMARY_VERIFICATION_COMMAND}}
```

Run after completing any task. Must exit 0 before phase can transition.

## Definition of Done (per phase)

1. Verification command passes (exit 0)
2. progress.md updated with evidence
3. init.sh passes with no warnings
4. No unfilled `{{` placeholders in modified files

## End of Session

1. Update `progress.md` with current state
2. Update `feature_list.json` if phase transition applicable (request human sign-off first)
3. Remove temporary/debug artifacts
4. Run `./init.sh` — confirm clean state
5. If ending mid-task, fill `session-handoff.md`

## Escalation

- **Scope ambiguity:** Re-read `feature_list.json` + `context/` docs
- **Tool not available:** Check `tools/mcp-allowlist.json` — may be phase-gated
- **Repeated failures (3+):** Update progress.md, flag for human review
- **Permission denied:** Do not retry. Note in progress.md and move on.
- {{DOMAIN_ESCALATION_RULES}}

## Domain Context

See `context/` directory for domain-specific knowledge:
- [context/README.md](context/README.md) — What belongs here
- {{DOMAIN_CONTEXT_LINKS}}
