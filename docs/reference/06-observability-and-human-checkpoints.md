# Observability and human-in-the-loop checkpoints

## Observability

Every decision (allow or deny) appends one JSON line to
`Harness-Best-Practice/observability/audit.log` via
`Harness-Best-Practice/observability/audit.py`. The model cannot rewrite it — it's the
accountability record.

## Human-in-the-loop checkpoints

The human doesn't approve every action — only three points:

1. **Phase sign-off** — agent reports "verification passes"; human flips
   `feature_list.json` status to `passing`.
2. **Escalation** — agent is stuck (3 failed attempts, or ambiguity); it stops and
   writes to `progress.md`.
3. **Policy update** — audit review reveals a gap; human edits the deny-list/allowlist.

Everything else is autonomous within the gates.

---
