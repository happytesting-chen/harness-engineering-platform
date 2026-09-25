# runtime-security-mvp — verification summary

What was built (Tasks 1–12 of the re-scoped plan), how it was proved, and what a
reviewer should check before the release verdict. This is the build-half record; the
claims batch and the signed verdict are the human half (below).

## Coverage

- **309 tests pass** repo-wide; 18 runtime suites under `tests/runtime/`.
- **Attack matrix: 13/13 RESISTANT** on side-effect oracles
  (`attack-traces.jsonl`, replayed in `replay-results.json`). Verdicts are derived from
  observed side effects, never from a model or classifier label.
- **`./init.sh`** exits 1 with the same 5-error baseline set as before this work — the
  fail-closed template baseline is unchanged; gate on the error set, not exit 0.
- **Classifier lock verifies** against artifacts and corpus digest
  (`eval_runtime_injection.py --verify` → PASS).

## The claims that hold, each with its proof

| Claim | Proof |
|---|---|
| Rule hit withholds without consulting the model | `test_ingress.py` — `classifier.calls == 0` |
| `unresolved + data` is the only ALLOW | `test_ingress.py` decision-table parametrization |
| Classifier timeout/crash/malformed → REQUIRE_REVIEW | `test_classifier.py` (13 failure shapes) |
| Content release ≠ action approval | `test_content_receipts.py`, `test_action_receipts.py` — type, key, context |
| An approval never converts DENY | `test_action_receipts.py::test_action_receipt_does_not_override_deny` |
| Session ceilings hold under concurrency | `test_guarded.py` — thread Barrier + asyncio gather races |
| A tainted turn cannot reach a USER_DIRECT-only sink | `test_source_sink_paths.py::test_taint_blocks_the_sink...` |
| No output byte leaves before screening | `test_output.py`, `test_host.py` |
| Audit chain detects tampering | `test_audit.py` — fails AT the doctored record |
| A fooled classifier is still RESISTANT (gate holds) | `test_replay.py::test_classifier_label_is_not_the_security_verdict` |
| No runtime module owns a duplicated detector | `test_claims_truthfulness.py`, per-module source scans |

## What a reviewer must check (plan Task 12 step 7)

Any open P0/P1 finding means the verdict is `DEPLOY_BLOCKED`. Review, at minimum:

1. Every source→sink row in `Context/runtime-security-profile.md` against
   `test_source_sink_paths.py` — is any sink reachable by a path the tests miss?
2. Receipt authority: can any receipt cross the content/action boundary, or survive a
   policy/rule/classifier drift? (`test_*_receipts.py`)
3. The startup invariants: is there a misconfiguration that starts anyway?
   (`test_startup.py`)
4. Every direct-call path into a tool that bypasses the guarded dispatcher — the
   `SEC-RUNTIME-GAP-001` surface. The tests prove the host routes correctly; they cannot
   prove an application will.
5. The output path: any release that is not buffered, any redaction that quotes its match.
6. Every claim in this file against its cited test.

## The human half — not done here, by design

- **Claims batch** (plan §5, Task 12 step 5): `control-matrix.md` tokens,
  `mechanisms.json`, `requirements.json`, and the `BUILTIN_PROTECTED_PATHS` additions for
  the new enforcement modules land as ONE human-applied change. `SEC-RUNTIME-GAP-001`
  stays GAP until an application's routing is proved — the code existing is not the same
  as an app going through it.
- **Verdict** (`VERDICT.md`): `PRODUCTION_READY` / `DEPLOY_WITH_RULES` / `DEPLOY_BLOCKED`,
  human-signed, scoped to one exact policy, classifier lock, source revision and profile.
  No verdict here applies to model-weight robustness, memory, delegation, binary
  documents, untested hosts, or deployments without control-plane isolation.
