# {{PROJECT_NAME}}

{{PROJECT_PURPOSE}}

## Startup Workflow

1. Confirm working directory with `pwd`
2. Read this file completely
3. Run `./init.sh` to verify environment is healthy
4. Read `feature_list.json` to see current phase/task state
5. Review recent commits with `git log --oneline -5`

If baseline verification is failing, repair that first before adding new scope.

## Working Rules

- **One task at a time**: only one entry in feature_list.json is ACTIVE
- **Verification required**: don't claim done without running the verification command
- **Update artifacts**: before ending session, update progress.md and feature_list.json
- **Stay in scope**: don't touch files unrelated to the current task
- **Leave clean state**: next session runs init.sh immediately with no manual fix

## Governance Boundaries

{{DENY_LIST_SUMMARY}}

See `governance/deny-list.json` for the machine-readable rules.
See `governance/permission.py` for the enforcement mechanism.

## Verification Commands

```bash
{{PRIMARY_VERIFICATION_COMMAND}}
```

## Escalation

- **Scope ambiguity**: re-read feature_list.json and context/target-scope.md
- **Tool not available**: check tools/mcp-allowlist.json — it may be phase-gated
- **Repeated failures**: update progress.md, flag for human review
- **Unclear requirements**: check context/ docs first, then ask the user
