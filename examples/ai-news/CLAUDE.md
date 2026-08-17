# {{PROJECT_NAME}}

{{PROJECT_PURPOSE}}

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

## Working Rules

- **WIP=1** — One task at a time. Finish or park before starting another.
- **Verify before claiming done** — Run the phase's verification command. Exit 0 = done.
- **Update progress.md** — Record what was done, decisions, and next steps before session end.
- **Stay in scope** — Only work within the active phase.
- **Leave clean state** — No temp files, no broken tests, no uncommitted debug code.

## Governance Boundaries

{{DENY_LIST_SUMMARY}}

Four enforcement gates fire on every tool call, in this order (mechanical, not advisory).
First denial wins; the gate fails closed.
1. **Protected paths** — the mechanism's own files are unwritable → `permission.py` `BUILTIN_PROTECTED_PATHS`
2. **Deny-list** — Hard-blocked patterns → `governance/deny-list.json`
3. **Phase-gate** — Tools locked until prerequisites pass → `governance/mcp-allowlist.json`
4. **Egress** — Outbound network default-deny → `governance/mcp-allowlist.json` egress_hosts

Gate 1 runs **first** and is the one that enforces S2.4 — the guarantee that the agent cannot
edit its own policy. A doc that lists only three gates omits the one that runs first.

## Verification Commands

```bash
{{PRIMARY_VERIFICATION_COMMAND}}
```

## End of Session

1. Update `Harness-Best-Practice/progress.md` with current state and decisions
2. Run `./init.sh` — confirm clean state
3. If phase complete: report "Phase X passes. Requesting sign-off." (do NOT self-transition)
4. If ending mid-task: fill the Session Handoff section in `Harness-Best-Practice/progress.md`

## Escalation

- **Scope ambiguity:** Re-read `Harness-Best-Practice/feature_list.json` + `Context/` docs
- **Tool not available:** Check `governance/mcp-allowlist.json` — may be phase-gated
- **Repeated failures (3+):** Update `Harness-Best-Practice/progress.md`, flag for human review
- **Permission denied:** Do not retry. Note in `Harness-Best-Practice/progress.md` and move on.
- {{DOMAIN_ESCALATION_RULES}}

## Reference

- [BEST-PRACTICES.md](Harness-Best-Practice/BEST-PRACTICES.md) — Harness engineering principles (generic, from Learn Harness Engineering)

## Domain Context

See `Context/` for **project-specific** AI-development assets — product/design, AI stack
(framework + model, e.g. LangChain/Strands), deployment target (on-prem/cloud),
architecture, methodology, scope. (Threat model and security controls live in `Security-kit/`.)
- [Context/README.md](Context/README.md) — What belongs here
- {{DOMAIN_CONTEXT_LINKS}}
