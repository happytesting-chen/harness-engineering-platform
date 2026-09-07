# Security Kit

## 1. What is this kit?

```
              ┌──────────────────────────────────────────────────┐
              │              THE ONE RULE                        │
              │   Reasoning proposes.  Mechanism enforces.       │
              │   The model is never a control surface.          │
              └──────────────────────────────────────────────────┘
```

The kit is **four parts answering four different questions**. They are separate because
they fail differently and are reviewed by different people.

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  ①  WHICH controls apply to THIS product?          decided by a MODEL, once      ║
║      /security-tailor  reads Context/                → coverage.json             ║
║                                                      → active-controls.md        ║
║      a human reviews the selection before it takes effect                        ║
╟──────────────────────────────────────────────────────────────────────────────────╢
║  ②  WHAT do those controls say?                    decided by PEOPLE, in advance ║
║      SECURITY.md            42 source-tagged controls (S1.1 – S8.6)              ║
║      owasp-crosswalk.md     OWASP LLM01–10 / ASI01–10 → mechanism, incl. gaps    ║
║      SECURITY-MANIFEST.md   what is security vs. domain                          ║
║      control-matrix.md      control → code → test → evidence  (fill per project) ║
╟──────────────────────────────────────────────────────────────────────────────────╢
║  ③  WHO enforces them, every call?                 decided by CODE               ║
║      governance/permission.py    control plane — 4 gates; also self-protects     ║
║                                  the mechanism from its own agent (S2.4)         ║
║      Security-kit/secret_scan.py credential block on write-shaped tools          ║
║      Security-kit/content_trust.py  data plane — owns the one marker list        ║
║      Security-kit/prompt_screen.py  ① the prompt, before the model reads it      ║
║      Security-kit/result_screen.py  ④ the tool result, before the model reads it ║
║      Security-kit/check_coverage.py completeness gate inside ./init.sh           ║
║      ─── and for the app you DEPLOY, where none of those hooks exist: ──────     ║
║      governance/runtime_dispatcher.py  ② ③ ④  one chokepoint your app calls      ║
║      Security-kit/runtime_screen.py    ① ④    request boundary + tool output     ║
╟──────────────────────────────────────────────────────────────────────────────────╢
║  ④  HOW DO WE KNOW it works?                       decided by EVIDENCE          ║
║      tests/     is the gate CORRECT?      ground-truth fixtures + hook drive     ║
║      demo/      does the gate MATTER?     gated run vs. `--nogate` run           ║
║      eval/      does selection WORK?      labelled corpus → recall / precision   ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

Two planes, because agents are attacked on both:

```
   CONTROL PLANE                          DATA PLANE
   "may this action execute?"             "can I trust what I just read?"
   tool calls, commands, egress           claim bodies, emails, documents

   governance/permission.py               Security-kit/content_trust.py
   ├─ intercepts the call                 ├─ never passes a tool gate — it is
   ├─ returns a VERDICT                   │  data, not a tool call
   └─ exit 2 = BLOCKED                    └─ returns a REPORT; caller decides
                                             (its docstring: "It does NOT
      MECHANICAL                              sanitize-and-trust. It reports.")
      wired + tested
                                             MECHANICAL via two adapters:
                                             `scan_text` is called by
                                             prompt_screen.py ① and
                                             result_screen.py ④, which DO act on
                                             the report (erase / replace).
                                             `screen_record` is still LIBRARY —
                                             nothing calls it.
```

### The kit by layer

Where each concern lives, from the template's point of view:

| Layer | Purpose | Where |
|---|---|---|
| **Context** | The approved posture, threats, controls | `Security-kit/SECURITY.md` (42 source-tagged controls, S1.1 – S8.6) |
| **Guidance** | Shape everyday coding behaviour | `kiro/steering/security.md` (Kiro auto); `.claude/rules/` (Claude, optional) |
| **Workflow** | Review sensitive changes consistently | `kiro/steering/security-review.md` |
| **Policy** | Permitted tools, egress, approvals | `governance/deny-list.json`, `governance/mcp-allowlist.json`, `Harness-Best-Practice/feature_list.json` |
| **Enforcement** | Prevent prohibited actions | `governance/permission.py` (control) + `Security-kit/content_trust.py` (data) — in your IDE session via hooks, in your deployed app via `governance/runtime_dispatcher.py` + `Security-kit/runtime_screen.py` |
| **Verification** | Prove controls work + resist attack | `tests/test_hooks.py`, `test_e2e.py`, `test_content_trust.py`, `test_runtime_dispatcher.py`, `test_runtime_screen.py`, `fixtures.json` |
| **Evidence** | Record decisions, findings, residual risk | `Security-kit/control-matrix.md`, `progress.md`, git history |

### Per project, and the kit as a whole

context, guidance, policy, enforcement, verification, and review evidence. It applies an
*approved* design; it doesn't make architecture decisions for you.

**Fill per project:** `Security-kit/coverage.json` — which of the 20 OWASP LLM/Agentic ids
apply here ([Step 5b](../README.md#step-5b--tailor-the-security-controls-security-tailor) drafts it) —
then the rows of `Security-kit/control-matrix.md` (control → code → verification →
evidence), your threat model, and any domain-specific test cases. The template ships the
matrix's per-project table **empty**: no placeholder row, because a stub row draws wrong
answers that no invariant can catch.

**AI-specific risk coverage.** `Security-kit/owasp-crosswalk.md` maps every item of the
**OWASP Top 10 for LLM Applications (2025)** and the **OWASP Top 10 for Agentic
Applications (2026, ASI01–ASI10)** to the exact template mechanism that addresses it —
marked `[MECH]` (enforced + tested), `[GUIDE]` (advisory), `[APP]` (your code), or
`[GAP]`. Use it to prove coverage and record residual risk.

**Security vs non-security.** `Security-kit/SECURITY-MANIFEST.md` is the authoritative
inventory: which files are pure-security (removable), which are pure-harness, and which
are *wired* (security woven into a shared file). To produce a build with the security
layer removed — for comparison, or a deliberately ungoverned project:

```bash
./install.sh --no-security --dry-run   # preview what's removed/neutralized
./install.sh --no-security             # strip it (run on a copy)
```

The full build's `init.sh` integrity gate prevents the kit from being *silently*
stripped; `--no-security` is the explicit, recorded way to remove it.

> A control is only **mechanical** when an execution path enforces it *and* a test proves
> that path. Steering and docs are *guidance*; hooks and tests are *enforcement*. `init.sh`
> now gates on the enforcement proofs so a disabled kit cannot pass silently.

Sources: AWS Well-Architected Agentic AI Lens, CSA Singapore "Securing Agentic AI"
Addendum, OWASP Agentic AI Top 10 — see `Security-kit/SECURITY.md` for the tagged mapping.

---

## 2. How does it work?

The full walkthrough moved to the platform reference so this file stays an index:

- [Security kit internals — from the agent loop to the dev-time enforcement path](../../docs/reference/02-build-time-enforcement.md)
- [The deployed runtime tier — the same gates with no hooks, and the semantic tier above them](../../docs/reference/03-deployed-runtime.md)
- [The claims plane — the tailoring path, what is mechanical, and the six invariants](../../docs/reference/04-claims-and-evidence.md)

The binding contract for the deployed profile is [`../Context/runtime-security-profile.md`](../Context/runtime-security-profile.md);
the measured record is [`../evaluation/runtime-security/`](../evaluation/runtime-security/).

## Use It

1. Follow the baseline guidance in [`SECURITY.md`](SECURITY.md) during development.
2. Fill [`control-matrix.md`](control-matrix.md) with the controls selected for the copied project.
3. Map risks to mechanisms with [`owasp-crosswalk.md`](owasp-crosswalk.md); see [`SECURITY-MANIFEST.md`](SECURITY-MANIFEST.md) for what is security vs domain.
4. For a security-sensitive change, manually include [`kiro/steering/security-review.md`](../kiro/steering/security-review.md) in Kiro before sign-off.
5. Record review evidence in the control matrix and the project handoff or approved review record.

## Assets

| Asset | Role | Type |
|---|---|---|
| `Security-kit/SECURITY.md` | Source-tagged baseline control guidance | Generic |
| `Security-kit/control-matrix.md` | Control-to-code, test, and evidence mapping | Fill per project |
| `.kiro/steering/security.md` | Concise always-on Kiro security guidance | Generic |
| `.kiro/steering/security-review.md` | Manual workflow for reviewing sensitive changes | Generic |
| `governance/`, `tools/`, `tests/` | Policy, enforcement, and verification mechanisms | Mixed |

## Boundaries

- Keep executable mechanisms in their functional directories; do not duplicate them here.
- Keep review decisions and non-sensitive evidence in Git; do not commit runtime audit logs, caches, sandbox output, or secrets.
- Treat a control as mechanical only when its execution path enforces it and tests prove that path.

## Tailored controls (security-tailor)

`/security-tailor` reads `Context/` and writes `coverage.json` — which OWASP-AI controls
apply to THIS product — plus a tailored `active-controls.md` the agent loads every session.
`check_coverage.py` gates `init.sh`: every `applies` control must map to a `control-matrix.md`
row with a real Verification.

**Boundary:** the gate enforces **completeness** (a verification is mapped), NOT **adequacy**
(that it is a good check). Adequacy stays with human review + sign-off. The skill decides
*applicability*; you supply the *verification*. Selection quality is measured in `Security-kit/eval/`.
