# Release verdict — runtime-security-mvp

> **STATUS: SIGNED — `DEPLOY_WITH_RULES`**, 2026-09-02, by shi_yuan@csa.gov.sg.
> This authorizes deployment of the `runtime-mvp` profile **only** under the five
> conditions in §5, **only** at the revision and policy digest named in §1, and **only**
> until the expiry in §5. Any condition unmet, or any scoped artifact changed, and this
> verdict does not apply — it does not lapse into `PRODUCTION_READY`, it lapses into
> nothing.

## 1. What is being judged

| Field | Value |
|---|---|
| Profile | `runtime-mvp` (deployed, in-process) — **not** the `demo` / IDE hook profile |
| Source revision | signed at `978eac839efef0fcc84a79fb51bb2b78d263f699`; **re-scoped to `8c93f75`** — see the amendment below |
| Policy digest | `65b90cd9f5d33d869ca50d784fa18d1e05a1710c3a592f74ae8360adc0898567` (sha256 of `deny-list.json` then `mcp-allowlist.json`) |
| Classifier lock | `Security-kit/runtime/semantic-model.lock.json`, signed `shi_yuan@csa.gov.sg` 2026-08-31 |
| Classifier artifact | `protectai/deberta-v3-base-prompt-injection-v2` ONNX, sha256 `f0ea7f23…047b228c` |
| Plan | `docs/superpowers/plans/2026-08-31-runtime-security-semantic-enforcement-rescoped.md`, Tasks 1–12 |

### Amendment A-1 — re-scope to the merge commit, 2026-09-02

The revision this verdict was signed at could not be its own merge commit: a verdict names
the tree it judges, and committing the verdict changes that tree. Two commits landed after
signing — the verdict document itself, and `64b0094`, which moved a standalone test runner
in `tests/runtime/test_host.py`. Neither is a C-5 artifact.

Verified before re-scoping, `978eac83` against `8c93f75`:

| C-5 artifact | Status |
|---|---|
| `Security-kit/runtime/` (all contents) | **unchanged** |
| `governance/deny-list.json` | **unchanged** |
| `governance/mcp-allowlist.json` | **unchanged** |
| `Security-kit/runtime/semantic-model.lock.json` | **unchanged** |

Complete diff between the two revisions: `VERDICT.md` and `tests/runtime/test_host.py`.
Nothing the verdict judges moved, so §2's evidence still describes this tree and the
decision in §5 carries over unmodified.

**Scope of this amendment:** the revision label in §1 only. The decision, the conditions,
the acceptances in §4 and the expiry are untouched — an amendment that altered any of
those would be a new verdict needing a new signature, not an amendment.

Recorded by the agent; the original signature stands and is not re-applied here.

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

Reviewer(s): agent-run, author of the code under review · Date: 2026-09-02 ·
Method: live adversarial attempts (scripts and greps), not code reading alone

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
| **R-1** | The classifier is the content-release authority for rule-clean content. Two measured confident misses (`atk-008`, `atk-010` — workflow-impersonation). A fooled classifier admits content; the deterministic action gate is then the only control, proven by the `classifier-false-negative` case. | **ACCEPTED** — managed by C-1. The action gate is the compensating control and is proven to hold on a fooled classifier. |
| **R-2** | Fail-closed ingress makes the review queue floodable. No queue bound in code; the deployment must state one or accept the load. | **ACCEPTED** — managed by C-3. F-1's fix gives the queue a drain; a *bound* is still the deployment's to state. |
| **R-3** | Semantic screening covers the `runtime-mvp` profile only. IDE/build-time hooks stay regex-only, deliberately. | **ACCEPTED** — no condition. The IDE profile is outside this verdict's scope; `demo` is not authorized by it. |
| **SEC-RUNTIME-GAP-001** | Routing is opt-in. Nothing forces an application through the host; a tool called directly is ungated. Remains **GAP**. | **ACCEPTED** — managed by C-1, which is why this is `DEPLOY_WITH_RULES` and not `PRODUCTION_READY`. Stays **GAP**. |
| **SEC-HARDEN-GAP-001** | No `/runtime-harden` drafter — per-project wiring is done by hand from SECURITY.md S1.6. | **ACCEPTED** — no condition. Hand-wiring per S1.6 is acceptable at this scale; C-1 verifies the result however it was produced. |

## 5. Decision

## **`DEPLOY_WITH_RULES`**

`PRODUCTION_READY` was not available: `SEC-RUNTIME-GAP-001` is open, and F-7 demonstrated
it concretely — raw tool callables remain reachable on a host instance and fire without
passing a gate. Nothing in the kit can force an application to route correctly, so the
routing guarantee must be carried by a condition on the deployment rather than by a claim
in the code. `DEPLOY_BLOCKED` was not warranted: no P0, and both P1s are closed.

### Conditions — all five are prerequisites, not aspirations

| # | Condition | How it is checked |
|---|---|---|
| **C-1** | **Every** tool invocation in the deployed application reaches its callable through `RuntimeHost.invoke_tool`. No component retains a reference to a raw tool callable, to `host._config.tools`, or to `dispatcher._inner._tools`. | Architecture review with a recorded code walkthrough naming every call site, filed in the deployment record. This is the condition the verdict rests on — F-7 shows the bypass is one attribute access away |
| **C-2** | The deployment runs with `production=True` and a `classifier_lock_path` pointing at the lock named in §1. | `validate_startup`'s `StartupReport.violations == ()` captured at first boot and filed in the deployment record |
| **C-3** | A review-queue bound is stated — depth cap, per-origin rate limit, or auto-expiry — **or** unbounded review load is accepted in writing with a named owner. | The bound, or the written acceptance, appears in the deployment record before first production traffic |
| **C-4** | An **independent** security review — not the author of the code — completes the §3 checklist. | Its findings are appended to §3. Any P0 it raises voids this verdict immediately; any P1 must be dispositioned before the expiry below |
| **C-5** | The scoped artifacts do not change: source revision, policy digest, classifier lock, and the contents of `Security-kit/runtime/`. | CI compares against §1; `eval_runtime_injection.py --lock … --verify` passes on every build |

### Expiry

**2026-12-01**, or immediately upon **any** of: a change to the source revision, policy
digest or classifier lock named in §1; a change under `Security-kit/runtime/`; or a P0
raised by C-4's independent review — whichever comes first.

Re-signature requires re-running §2's evidence and re-verifying §3. The expiry exists
because evidence has a shelf life: every number in §2 was measured against one tree, and a
verdict that outlives its measurements is an assertion, not a finding.

**Signed:** shi_yuan@csa.gov.sg · Security Programme Lead · 2026-09-02

*Recorded by the agent at the signatory's instruction. The decision, the conditions and
the §4 acceptances are the signatory's. The agent authored the §2 evidence and the §3
findings — which is precisely why C-4 requires an independent pass.*

## 6. What no verdict here covers

Regardless of the decision above, this verdict says nothing about: model-weight
robustness; operating-system confinement or sandboxing; persistent memory, delegation,
binary-document extraction, multi-host operation or streaming output (all
startup-disabled); deployments without the required read-only control plane; or attack
classes outside the 13-case matrix. **The matrix is a floor, not a ceiling — the absence
of a case is not evidence of resistance.**
