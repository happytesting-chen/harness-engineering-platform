# Release verdict — runtime-security-mvp

> **STATUS: UNSIGNED DRAFT.** The evidence sections below are pre-filled and verifiable.
> The findings, decision, scope and signature are the reviewer's to complete. An unsigned
> verdict authorizes nothing: until §5 carries a name and a date, this profile has **no
> release decision**, and `SEC-RUNTIME-GAP-001` plus every residual in §4 stands.

## 1. What is being judged

| Field | Value |
|---|---|
| Profile | `runtime-mvp` (deployed, in-process) — **not** the `demo` / IDE hook profile |
| Source revision | *(fill: `git rev-parse HEAD` at sign-off)* |
| Policy digest | *(fill: digest of the `governance/` policy pair in force)* |
| Classifier lock | `Security-kit/runtime/semantic-model.lock.json`, signed `shi_yuan@csa.gov.sg` 2026-08-31 |
| Classifier artifact | `protectai/deberta-v3-base-prompt-injection-v2` ONNX, sha256 `f0ea7f23…047b228c` |
| Plan | `docs/superpowers/plans/2026-08-31-runtime-security-semantic-enforcement-rescoped.md`, Tasks 1–12 |

## 2. Evidence (measured, reproducible)

| Check | Result | Command |
|---|---|---|
| Test suite | **315 passed** (18 runtime suites; 309 + 6 added by the F-1/F-4 fixes) | `python3 -m pytest tests -q` |
| Attack matrix | **13/13 RESISTANT** on side-effect oracles | `python3 Security-kit/runtime/attack_driver.py --output /tmp/t.jsonl` |
| Replay determinism | traces byte-identical on re-run | `python3 -m pytest tests/runtime/test_replay.py -q` |
| Classifier lock | PASS against artifacts + corpus digest | `eval_runtime_injection.py --lock … --verify` |
| Detection (corpus) | rule-only 12/16 → combined **14/16** attacks; 3/8 legitimate withheld | `evaluation/runtime-security/classifier-selection.md` |
| Build gate | exit 1, **unchanged 5-error baseline** (unfilled-template placeholders + fail-closed coverage) | `./init.sh` |
| Claims plane | **I1–I6 green**; 18 register rows, 30 matrix rows | `python3 Security-kit/check_coverage.py` |
| Self-protection | **28** protected paths; 158/392 shell cells open (60% closed) | `python3 -m pytest tests/test_protected_paths.py -q` |

Supporting documents: `verification-summary.md` (each claim → its proof, plus the reviewer
checklist), `limitations.md` (every disabled/untested capability), `attack-traces.jsonl`,
`replay-results.json`, `classifier-selection.md`.

## 3. Review findings

> Task 12 step 7. **Any open P0/P1 finding means `DEPLOY_BLOCKED`.** Work the checklist in
> `verification-summary.md` §"What a reviewer must check". Record every finding, including
> those judged acceptable — a finding omitted is a finding unmanaged.

Six checks were run on 2026-09-01 as live attempts (adversarial scripts and greps), not
as readings. **No P0.** Two P1s, both the same root cause: the profile written in Task 1
described a host that Task 11 did not build. Both are now fixed in code.

| # | Sev | Finding | Disposition |
|---|---|---|---|
| F-1 | P1 | Profile claimed quarantined content was releasable by receipt, but the host had **no redemption path** — `receipts=` was never passed. Fail-closed ingress had no drain: the first false positive stranded the session. | **FIXED** — `RuntimeHost.issue_release_receipt` + `release_quarantined`; 3 tests, incl. single-use and that release does not launder origin |
| F-2 | P2 | Profile listed "Structured record" as a source→sink row with no host method. | **ACCEPTED** — profile corrected to name `adapters.ingress_structured_record` as the application's call |
| F-3 | — | Receipt authority: 12 crossing attempts (type both ways, replay, policy/rule/classifier drift, expiry, digest, origin, stripped signature, tamper, forged key) all refused; valid control passes. | No finding |
| F-4 | P1 | The host accepted **any** classifier object and explicitly skipped lock verification (`semantic_enabled=False`). A remote/hosted classifier — or a stub always answering `data` — started successfully, while the profile claimed that was disabled. | **FIXED** — production requires `classifier_lock_path` and verifies artifact digests; 3 tests, incl. digest drift |
| F-5 | P3 | Profile forbade multi-host; two hosts construct fine, and a library cannot prevent it. | **ACCEPTED** — profile corrected to "out of scope, not enforced" |
| F-6 | P3 | Profile said binary ingress is a startup error; it is enforced at the **contract** layer per envelope. | **ACCEPTED** — profile corrected; enforcement is real, the location was misstated |
| F-7 | P3 | Raw tool callables reachable via `host._config.tools` and `_dispatcher._inner._tools` — both fired, bypassing every gate. | **ACCEPTED** — this is `SEC-RUNTIME-GAP-001`, now concretely demonstrated. An application can do this to itself; the model cannot (string-only surface, tested) |
| F-8 | — | Output: exactly one `transport.send`, inside `BufferedSender.release`. Three credential shapes redacted, none echoed in text or `repr`. | No finding |
| F-9 | — | 12/12 documented claims backed by their cited test, each asserting the specific property. | No finding |

Post-fix gate: **315 passed**; `./init.sh` at the unchanged 5-error baseline; I1–I6 green.

Reviewer(s): *(fill — see caveat)* · Date(s): *(fill)* · Method: *(code read / independent test / both)*

> **Caveat on independence.** Checks F-1…F-9 were run by the agent that wrote the code.
> Self-review catches omissions, not blind spots — and the two P1s found here were both
> the author's own Task-1-vs-Task-11 mismatch, which is precisely the kind of error
> self-review is worst at finding systematically. Plan Task 12 step 7 calls for an
> **independent** security review. Signing without one is a decision to accept
> author-run verification, and the verdict should say so.

## 4. Residuals carried into the decision

Each is measured and documented; none is a surprise. A verdict must state whether it
accepts them.

| ID | Residual | Accepted? |
|---|---|---|
| **R-1** | The classifier is the content-release authority for rule-clean content. Two measured confident misses (`atk-008`, `atk-010` — workflow-impersonation). A fooled classifier admits content; the deterministic action gate is then the only control, proven by the `classifier-false-negative` case. | *(fill)* |
| **R-2** | Fail-closed ingress makes the review queue floodable. No queue bound in code; the deployment must state one or accept the load. | *(fill)* |
| **R-3** | Semantic screening covers the `runtime-mvp` profile only. IDE/build-time hooks stay regex-only, deliberately. | *(fill)* |
| **SEC-RUNTIME-GAP-001** | Routing is opt-in. Nothing forces an application through the host; a tool called directly is ungated. Remains **GAP**. | *(fill)* |
| **SEC-HARDEN-GAP-001** | No `/runtime-harden` drafter — per-project wiring is done by hand from SECURITY.md S1.6. | *(fill)* |

## 5. Decision

Select exactly one. Delete the other two.

- [ ] **`PRODUCTION_READY`** — for the constrained `runtime-mvp` profile and only its
      documented deployment.
- [ ] **`DEPLOY_WITH_RULES`** — with the explicit, enforceable conditions and expiry below.
- [ ] **`DEPLOY_BLOCKED`**.

**Conditions (if `DEPLOY_WITH_RULES`):** *(each must be enforceable and checkable, not an
intention — e.g. "architecture review confirms every tool call routes through
`RuntimeHost.invoke_tool`, evidenced by a code walkthrough recorded in the deployment
record")*

1. *(fill)*

**Expiry:** *(fill — a verdict without an expiry outlives the evidence it rests on)*

**Signed:** *(name)* · *(role)* · *(date)*

## 6. What no verdict here covers

Regardless of the decision above, this verdict says nothing about: model-weight
robustness; operating-system confinement or sandboxing; persistent memory, delegation,
binary-document extraction, multi-host operation or streaming output (all
startup-disabled); deployments without the required read-only control plane; or attack
classes outside the 13-case matrix. **The matrix is a floor, not a ceiling — the absence
of a case is not evidence of resistance.**
