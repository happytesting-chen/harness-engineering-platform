# Template Evaluation Report — Claude Code

**Author:** Claude Code session, branch `reorg/claude-native`
**Date:** 2026-08-03
**Device under test:** `template/` (the Harness Engineering Platform template)
**Method:** live A/B build of a real agent + empirical defect testing
**Companion:** [`CLAUDE-SESSION-HANDOFF.md`](CLAUDE-SESSION-HANDOFF.md) (two-runtime reconciliation with the Kiro session)

---

## 1. Questions asked

1. Can Claude follow the template to build an AI agent successfully?
2. Does the `security/` layer guide the built agent to be more secure?
3. Is anything over-engineered or broken?

## 2. Method

A reduced, offline **claims-triage agent** (a local slice of the AWS event-driven
claims sample — all cloud stripped, every trust boundary kept) was used as the probe.
Two builds, single variable = the security apparatus:

- **Arm A (control):** template with the whole security apparatus removed (governance
  gates, security context/steering, security kit), reduced to a coherent bare scaffold.
- **Arm B (treatment):** the full reorganized template.

Both builds were run by independent fresh subagents given the **byte-identical task
prompt**, each told to dogfood its copy's `CLAUDE.md`. A **blind** security reviewer
(not told which build had what) scored both on a 12-dimension, 24-point rubric.

Validity notes: n=1 domain, stochastic builders → results are directional, not
statistically significant. The A/B measures the kit's **marginal** lift over Claude's
already-security-trained baseline — which is why domain-specific discriminators (the
$100k rule, the exact egress target, injection markers) matter.

## 3. Result

| | Arm A (no kit) | Arm B (full template) |
|---|---|---|
| Built a working, verified phase-01 agent? | Yes (init + verify exit 0) | Yes (init + verify exit 0) |
| **Blind security score** | **16 / 24** | **24 / 24** |
| Governance infra (egress / gates / secrets) | 2 / 6 | 6 / 6 |
| Prompt-injection resistance | 1 / 2 | 2 / 2 |
| Documentation / traceability | 1 / 2 | 2 / 2 |

**Security-kit value = +8 points (+50%).**

### Attribution (why this is causal, not coincidental)
- **Arm A builder:** controls came from *"the build task + my own judgment… the
  template only vaguely gestures at governance… the harness provides no mechanical
  enforcement."*
- **Arm B builder:** cited specific template files — *"guided by `context/SECURITY.md`
  S1.4,"* filled the 7-row control matrix, extended the deny-list; and the **live hooks
  fired on it** (its `curl`/`rm` test commands were blocked mid-build), proving the
  fixed enforcement path works end-to-end in a real Claude session.

## 4. Answers

1. **Can Claude build from the template? Yes** — both arms produced correct, verified
   agents. The harness primitives (feature_list triple, progress.md, WIP=1, human
   sign-off, init.sh) held in both.
2. **Does `security/` help? Yes, measurably** — same task/model/spec, +8 security
   points, with builder attribution confirming the kit (not chance) caused the lift.
3. **Over-engineering / breakage: yes, real gaps** — see §6.

## 5. Template defects found AND fixed this session (Claude enforcement path)

The Claude Code enforcement path shipped **broken and never-exercised** (all tests
bypassed the hooks via the Python API). Fixed on `reorg/claude-native`, each proven:

| Defect | Fix | Proof |
|---|---|---|
| Hook fed literal `$TOOL_NAME` → malformed JSON → crash | `settings.json` pipes real stdin to `permission.py` | `test_hooks.py` |
| Crash = exit 1 = **fails open** | `permission.py` **fails closed** (exit 2) on bad input | `test_hooks.py` |
| Tool-name casing (`Bash`≠`bash`) denied everything | normalization map | `test_hooks.py` |
| Audit logged literal `$TOOL_NAME` | `audit_hook.py` records real name | `test_hooks.py` |
| Secret regex missed escaped-JSON content | `secret_scan.py` decodes first | `test_hooks.py` |
| **Missing integration test** (root cause) | added `tests/test_hooks.py` (10 cases) | 10/10 pass |

Plus a **reorganization** to Claude-native root + `kiro/` opt-in (nothing inert in the
active root; `CLAUDE.md` imports `@AGENTS.md`). Verified 13/13 by a fresh session.

**Process finding — bootstrap-ordering brick:** the two-file fix (settings.json +
permission.py) cannot be safely applied *from inside* a Claude session governed by that
same settings.json — either half-applied state bricks tool use (observed in both
directions). Repair requires a session without the hooks live, or an atomic swap.

## 6. Gaps found by the A/B — ALL FIXED (verified 12/12, fresh session)

Ordered by importance. Both builders independently converged on #1 and #2.
Status added 2026-08-03 after the fix pass on `reorg/claude-native`.

**G1 — Threat model is tool-call-oriented; content injection is invisible to all gates.** `[FIXED]`
`governance/permission.py` gates commands/tools/egress. The claims agent's primary
threat — injected instructions inside `inbox/claim.json` — is **data, not a tool call**,
so it passed through all three gates untouched. Injection defense fell entirely to
hand-written app logic; the template had no content/data-flow trust primitive.
**Fix:** added `governance/content_trust.py` — a data-plane boundary
(`screen_record()`: field allowlisting + injection-marker detection) that complements
permission.py's control plane. Guidance in `context/SECURITY.md`; proven by
`tests/test_content_trust.py` (6 tests). It reports; the caller fails toward review.

**G2 — `init.sh` verified governance *files exist*, not that enforcement is *wired/functional*.** `[FIXED]`
`init.sh` required the two governance JSON files but not `permission.py` itself, the
`.claude/settings.json` hook wiring, or a passing hook proof — so enforcement could be
gutted and init.sh still exited 0 (exactly what Arm A demonstrated).
**Fix:** new "Security-kit integrity" section in `init.sh` fails unless (a) `permission.py`
present, (b) settings.json wires it, (c) `test_hooks.py` passes, (d) `test_content_trust.py`
passes. A stripped kit now fails init.sh instead of reporting PASS.

**G3 — Placeholder inconsistency.** `[FIXED]`
README now uses `{{PRIMARY_VERIFICATION_COMMAND}}` (matching CLAUDE.md); `AGENTS.md`
added to `init.sh`'s placeholder scan.

**G4 — Stale breadcrumb.** `[FIXED]`
`tests/fixtures.json` `_comment` corrected — it no longer references the nonexistent
`tests/policies/`; states the runner provisions policy in-memory.

**G5 — Deny-list was naive substring match.** `[FIXED]`
`check_deny_list` now supports `{"pattern","mode"}` entries with `word` (boundary) and
`regex` modes alongside plain-string substring (backward-compatible). A malformed regex
falls back to substring so the gate never crashes. `curl` in `word` mode no longer fires
on `curly`. Verified.

## 7. Outcome

- **All 5 gaps fixed on `reorg/claude-native`**, verified 12/12 by a fresh Claude session
  (structure, syntax, deny-list substring + new word mode, content-trust 6/6, hooks 10/10,
  fixtures 7/7, e2e 3/3, integrity block all ✓). Existing suites unbroken.
- G1 + G2 (both builders' core complaints) are addressed at root cause: the template now
  has a **data-plane** trust boundary in addition to its control-plane gates, and `init.sh`
  **runs the enforcement proof as a gate** so an ungoverned agent can no longer pass.
- `reorg/claude-native` committed + pushed; merge/PR pending human review.

## 8. Artifacts

- Reorg branch `reorg/claude-native` (uncommitted at time of writing).
- Build outputs: `/tmp/arm-a` (control), `/tmp/arm-b` (treatment).
- Two-runtime reconciliation: `CLAUDE-SESSION-HANDOFF.md`.
