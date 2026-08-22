# Tests Module

Verification infrastructure. 18 suites: data-driven gate tests, E2E enforcement proofs,
detection-quality measurement, and the claims-register invariants.

## Responsibilities

- Fixture-driven testing: ground-truth dataset drives all permission gate validation
- E2E enforcement: prove the gate PREVENTS execution, not just logs denial (Day 4 pattern)
- Prove **both** enforcement layers: the hook path in a Claude Code session, and the
  in-process path a deployed application calls
- Measure what is not exact: detection recall/precision against a labelled corpus
- Extensible per domain: add cases to `fixtures.json`, no new test code needed

## The prevention convention (why these tests look the way they do)

A test that only inspects a return value cannot tell "the gate refused" from "the gate
allowed and the tool happened to return an error". So a denial test counts **calls**:

```python
assert calls == 0     # gate ② refused — the side effect never happened
assert calls == 1     # gate ④ withheld the output — the tool DID run
```

That distinction is the whole difference between the action plane and the data plane, and
it is the reason `test_runtime_dispatcher.py` and `test_e2e.py` use call counters rather
than asserting on messages. See `Security-kit/SECURITY.md` S8.4.

## Files

Zero external dependencies. Each file runs standalone (`python3 tests/test_x.py`) *and*
under pytest; `pytest` is never required for a test to pass.

| File | Tests | Role | Modify? |
|------|-------|------|---------|
| `fixtures.json` | — | Ground-truth test cases (tool, input, expected decision) | **Extend** per domain |
| `test_fixtures.py` | 1 | Reads fixtures.json, asserts each case against the real permission gate | **Never** |
| `test_e2e.py` | 4 | Day 4 pattern: denied call → no side effects, removing gate → test fails | **Never** |
| `test_hooks.py` | 15 | Hook integration — drives `permission.py` and `secret_scan.py` as subprocesses over stdin, asserts on the **exit code** | **Never** |
| `test_protected_paths.py` | 23 | Gate 1a by file identity — traversal, absolute, symlink, hard-link, case variants | **Never** |
| `test_egress.py` | 19 | Gate 3 — shell tokens plus the 9 structured destination fields, nested | **Never** |
| `test_steady_state.py` | 9 | Phase-gate escalation attempts all DENY (worklog edits buy no privilege) | **Never** |
| `test_shipped_policy.py` | 7 | The policy files **as shipped**, not as fixtured | **Never** |
| `test_content_trust.py` | 6 | Data-plane library — `scan_text`, `screen_record` | **Never** |
| `test_prompt_screen.py` | 10 | ① hook — exit 2 erases the prompt; no pattern of its own (anti-drift) | **Never** |
| `test_result_screen.py` | 18 | ④ hook — `updatedToolOutput` substitution, shape-preserving | **Never** |
| `test_result_screening.py` | 9 | ④ screening behaviour end to end | **Never** |
| `test_runtime_screen.py` | 17 | Deployed ① and ④ — fails closed on non-`str`, no warn mode | **Never** |
| `test_runtime_dispatcher.py` | 20 | Deployed ② ③ ④ — `PermissionError` before the call, `calls == 0` | **Never** |
| `test_injection_corpus.py` | 7 | Detection recall/precision against the labelled corpus | **Never** |
| `test_coverage.py` | 1 | Coverage gate — unit + integration | **Never** |
| `test_eval_selection.py` | 1 | Selection benchmark recall | **Never** |
| `test_mechanisms.py` | 1 | Claims-register invariants I1–I5 + the matrix census | **Never** |
| `test_requirements.py` | 1 | Invariant I6, both directions | **Never** |

> **`init.sh` names 15 of these 18 individually.** `test_mechanisms.py`,
> `test_requirements.py` and `test_result_screening.py` are not reached by the gate — they
> pass under `pytest tests/` but a regression in them does not fail `./init.sh`. Tracked as
> `SEC-PROOF-GAP-001`. Adding a suite is not the same as gating on it.

## Running

```bash
python3 tests/test_fixtures.py            # Data-driven permission gate tests
python3 tests/test_e2e.py                 # E2E enforcement proof (4 tests)
python3 tests/test_runtime_dispatcher.py  # Deployed-runtime gates ② ③ ④ (20 tests)
python3 tests/test_runtime_screen.py      # Deployed-runtime gates ① ④ (17 tests)
python3 -m pytest tests/ -q               # All 18 suites
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
