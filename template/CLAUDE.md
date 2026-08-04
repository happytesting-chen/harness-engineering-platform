# {{PROJECT_NAME}}

{{PROJECT_PURPOSE}}

<!-- System identity (tech stack, architecture, hard constraints) lives in AGENTS.md,
     the open standard other agents read. Import it so Claude loads it too, rather
     than duplicating it here. This CLAUDE.md adds the Claude-specific session workflow. -->
@AGENTS.md

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
2. **Phase-gate** — Tools locked until prerequisites pass → `governance/mcp-allowlist.json`
3. **Egress** — Outbound network default-deny → `governance/mcp-allowlist.json` egress_hosts

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
- **Tool not available:** Check `governance/mcp-allowlist.json` — may be phase-gated
- **Repeated failures (3+):** Update progress.md, flag for human review
- **Permission denied:** Do not retry. Note in progress.md and move on.
- {{DOMAIN_ESCALATION_RULES}}

## Reference

- [BEST-PRACTICES.md](BEST-PRACTICES.md) — Harness engineering principles (generic, from Learn Harness Engineering)

## Domain Context

See `context/` for **project-specific** AI-development assets — product/design, AI stack
(framework + model, e.g. LangChain/Strands), deployment target (on-prem/cloud),
architecture, methodology, scope. (Threat model and security controls live in `security/`.)
- [Context/README.md](Context/README.md) — What belongs here
- {{DOMAIN_CONTEXT_LINKS}}
