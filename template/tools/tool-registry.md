# Tool Registry

Document every external tool integration here. Tools must be vetted and version-pinned before use.

## Vetting Process

1. **Identify** — Tool name, purpose, source repository
2. **Review** — Check for known vulnerabilities, licence compatibility, maintenance status
3. **Pin version** — Lock to a specific reviewed version in `mcp-allowlist.json`
4. **Approve** — Record approval rationale and reviewer below
5. **Register** — Add to `mcp-allowlist.json` with optional `gated_until` constraint

## Registry

| Tool | Version | Review Status | Reviewer | Approval Date | Rationale |
|------|---------|--------------|----------|---------------|-----------|
| (tool name) | (pinned version) | Pending / Approved / Rejected | (name) | (date) | (why approved or rejected) |

## Rules

- No tool executes without an entry in `mcp-allowlist.json`
- Version must match what was reviewed — updates require re-review
- Phase-gated tools (`gated_until`) require their prerequisite phase to pass before use
- Rejected tools are recorded here with rationale (for audit trail)
