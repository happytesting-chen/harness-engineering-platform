# Observability Module

Append-only audit logging. Every tool call decision (allowed or denied) gets one JSON-lines entry.

## Responsibilities

- Record tool call decisions with timestamp, tool, args, decision, reason
- Never read, overwrite, truncate, or delete existing entries
- Provide compliance-reviewable history of all agent actions

## Files

| File | Role | Modify? |
|------|------|---------|
| `audit.py` | Logging mechanism — append one JSON line per call | **Never** per project |
| `audit.log` | Output — generated at runtime, append-only | **Never** edit manually |

## Interface

```python
from observability.audit import record

record(event="tool_call", tool="bash", detail={"command": "ls"}, decision="ALLOWED", reason="")
```

## Constraints

- MUST NOT import external packages (stdlib only)
- MUST append only — never overwrite or truncate
- Audit failure MUST NOT halt the agent (log warning, continue)
- One JSON object per line (JSON-lines format)
