---
inclusion: auto
---

# Session Cycle

> Purpose: Standard workflow for every work session — ensures consistent startup, execution, and clean exit.

## Startup

1. Read `CLAUDE.md` for project rules and governance boundaries
2. Run `./init.sh` — **must exit 0** before proceeding
3. Read `Harness-Best-Practice/feature_list.json` — identify the one phase with status `"active"`
4. Read `Harness-Best-Practice/progress.md` — understand current state, decisions, and blockers
5. If the Session Handoff section has content, resume from there

## Execution

6. Pick one task from the active phase (WIP=1 — one task only)
7. Work on the task within scope boundaries
8. After completing: run the verification command from `feature_list.json`
   - **Check:** Verification must exit 0 before claiming done
9. Update `progress.md` — record what was done, decisions made, and next steps

## Exit

10. Run `./init.sh` one final time — confirm clean state
    - **Check:** Must exit 0 with no placeholder warnings
11. If the phase is complete (all tasks done, verification passes):
    - Report to the user: "Phase X verification passes. Requesting sign-off."
    - **Do NOT self-transition** — wait for human to update feature_list.json
11b. Before requesting sign-off, if this phase added a tool, egress host, data flow,
     retrieval, or untrusted input: re-run **`/security-tailor`** and resolve any new
     `applies` control (fill its Verification). `./init.sh` will fail until coverage is complete.
12. If ending mid-task: fill the Session Handoff section in `progress.md`

## Exit Condition

Session ends when ANY of these is true:
- Task verified, progress.md updated, init.sh passes
- A blocker prevents further progress (recorded in progress.md)
- Human requests stop
- Phase complete and awaiting sign-off
