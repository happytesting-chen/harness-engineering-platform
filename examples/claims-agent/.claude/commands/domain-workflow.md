# {{DOMAIN_WORKFLOW_NAME}}

> Purpose: {{DOMAIN_WORKFLOW_PURPOSE}}

## Prerequisites

- Active phase in feature_list.json matches this workflow's scope
- init.sh passes (exit 0)
- Required tools available (check mcp-allowlist.json)

## Workflow Steps

{{DOMAIN_WORKFLOW_STEPS}}

## Verification Between Steps

{{STEP_VERIFICATION_CHECKS}}

## Exit Condition

{{DOMAIN_EXIT_CONDITION}}

## Escalation

- If a step fails 3 times: record in progress.md and flag for human review
- If scope is ambiguous: re-read context/ documents before proceeding
- If a required tool is unavailable: check phase-gate status in mcp-allowlist.json
