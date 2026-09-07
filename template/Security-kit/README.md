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

## 2. How does it work?

The full walkthrough moved to the platform reference so this file stays an index:

- [Security kit internals — from the agent loop to the dev-time enforcement path](../../docs/reference/04-security-kit-internals.md)
- [The deployed runtime tier — the same gates with no hooks, and the semantic tier above them](../../docs/reference/02-deployed-runtime-tier.md)
- [The claims plane — the tailoring path, what is mechanical, and the six invariants](../../docs/reference/03-claims-plane.md)

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
