# Tests Module

Verification infrastructure. Data-driven tests + E2E enforcement proof.

## Responsibilities

- Fixture-driven testing: ground-truth dataset drives all permission gate validation
- E2E enforcement: prove the gate PREVENTS execution, not just logs denial (Day 4 pattern)
- Extensible per domain: add cases to `fixtures.json`, no new test code needed

## Files

| File | Role | Modify? |
|------|------|---------|
| `fixtures.json` | Ground-truth test cases (tool, input, expected decision) | **Extend** per domain |
| `test_fixtures.py` | Reads fixtures.json, asserts each case against real permission gate | **Never** |
| `test_e2e.py` | Day 4 pattern: denied call → no side effects, removing gate → test fails | **Never** |

## Running

```bash
python3 tests/test_fixtures.py   # Data-driven permission gate tests
python3 tests/test_e2e.py        # E2E enforcement proof (3 tests)
python3 -m pytest tests/ -v      # Both via pytest
```

## Extending

Add domain-specific cases to `fixtures.json`:
```json
{
  "description": "your test case name",
  "tool": "tool_name",
  "input": {"command": "the command"},
  "expected_decision": "ALLOWED or DENIED",
  "expected_gate": "deny-list | phase-gate | egress | null",
  "expected_reason": "expected reason substring"
}
```

No new test code required — the data-driven runner picks up new cases automatically.
