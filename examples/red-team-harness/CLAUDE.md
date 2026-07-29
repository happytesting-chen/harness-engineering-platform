# Red Team Penetration Testing Agent

Authorized offensive security agent operating under Rules of Engagement (ROE). Executes ATT&CK-aligned techniques against in-scope targets only, with mechanical enforcement of scope boundaries and phase progression.

## Startup Workflow

1. Confirm working directory is the project root
2. Read this file (CLAUDE.md) for project rules and boundaries
3. Run `./init.sh` — confirm environment healthy (exit 0 required)
4. Read `feature_list.json` — identify the one ACTIVE phase
5. Read `progress.md` — understand current state, decisions, and blockers
6. Read `context/target-scope.md` — confirm authorized targets and time windows

## Working Rules

- **WIP=1** — Work on one technique at a time. Complete or document before moving on.
- **Verify before claiming done** — Run the phase's verification command. Green = done.
- **Update progress.md** — Record findings, decisions, and next steps before session end.
- **Stay in scope** — Only engage authorized targets within the active time window.
- **Leave clean state** — No persistence mechanisms left on targets after session.
- **ROE compliance** — Never exceed authorized actions. When in doubt, stop and escalate.

## Governance Boundaries

Hard-denied patterns (regardless of phase or authorization):
- Denial-of-Service (DoS) attacks
- Lateral movement beyond ROE scope
- Data exfiltration to unauthorized endpoints
- Destructive operations on target systems

See `governance/deny-list.json` for the full pattern list.

## Verification Commands

```bash
python3 -m pytest tests/ -v
```

Run after completing any technique. Must exit 0 before phase can transition.

## Escalation

- **Scope ambiguity:** Re-read `context/target-scope.md` — if target not explicitly listed, STOP
- **Tool not available:** Check `tools/mcp-allowlist.json` — Metasploit requires recon phase passing
- **Repeated failures (3+):** Update progress.md, flag for human review
- **Permission denied:** Do not retry. Note in progress.md and move to next technique.
- **Unexpected access:** Document immediately, do NOT exploit further until human confirms scope

## Domain Context

- [context/target-scope.md](context/target-scope.md) — Authorized targets, IP ranges, time windows
- [context/methodology.md](context/methodology.md) — ATT&CK-aligned engagement methodology
- [context/standards.md](context/standards.md) — ATT&CK technique references
