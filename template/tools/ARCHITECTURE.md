# Tools Module

Tool registry and egress control policy.

## Responsibilities

- Define which tools are permitted (allowlist)
- Define phase-gate constraints (which tools require prerequisites)
- Define approved outbound network hosts (egress allowlist)

## Files

| File | Role | Modify? |
|------|------|---------|
| `mcp-allowlist.json` | Tool permissions + egress hosts | **Always** fill per domain |

## Schema

```json
{
  "tools": [
    {
      "name": "tool_name",
      "description": "what it does",
      "version": "pinned version",
      "gated_until": "optional — phase ID that must be 'passing'"
    }
  ],
  "egress_hosts": ["allowed outbound hosts/IPs"]
}
```

## Constraints

- Tools NOT in this file are denied by the phase-gate
- `gated_until` references a phase ID in `feature_list.json`
- `egress_hosts` uses substring matching against the full command
- Adding a tool here requires domain expert review (supply-chain vetting)
