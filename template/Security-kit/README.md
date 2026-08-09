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
║      SECURITY.md            41 source-tagged controls (S1.1 – S8.6)              ║
║      owasp-crosswalk.md     OWASP LLM01–10 / ASI01–10 → mechanism, incl. gaps    ║
║      SECURITY-MANIFEST.md   what is security vs. domain                          ║
║      control-matrix.md      control → code → test → evidence  (fill per project) ║
╟──────────────────────────────────────────────────────────────────────────────────╢
║  ③  WHO enforces them at runtime?                  decided by CODE, every call   ║
║      governance/permission.py    control plane — 4 gates; also self-protects     ║
║                                  the mechanism from its own agent (S2.4)         ║
║      Security-kit/secret_scan.py credential block on write-shaped tools          ║
║      Security-kit/content_trust.py  data plane — screens untrusted content       ║
║      Security-kit/check_coverage.py completeness gate inside ./init.sh           ║
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
      wired + tested                          LIBRARY — not wired into any path yet
```

## 2. How does it work?

### The enforcement path (dev-time, live today)

```
  agent decides to act
        │
        ▼
  ┌──────────────┐   PreToolUse fires ONLY for these five tools:
  │  tool call   │   Bash | Write | Edit | MultiEdit | NotebookEdit
  └──────┬───────┘   (the `matcher` in .claude/settings.json)
         │
         │  JSON envelope on stdin: {"tool_name": …, "tool_input": {…}}
         │
         ├───────────────────────────────┬──────────────────────────────┐
         ▼                               ▼                              │
 ╔═════════════════════════════╗  ╔═══════════════════════════╗         │
 ║ governance/permission.py    ║  ║ Security-kit/             ║         │
 ║ four gates, in order,       ║  ║   secret_scan.py          ║         │
 ║ FIRST DENIAL WINS           ║  ║ credential patterns in    ║         │
 ║                             ║  ║ content / command /       ║         │
 ║ ①a protected paths  (S2.4)  ║  ║ new_string                ║         │
 ║ ①b deny-list  command pats  ║  ╚═════════════╤═════════════╝         │
 ║ ②  phase-gate               ║                │                       │
 ║ ③  egress                   ║                │                       │
 ╚══════════════╤══════════════╝                │                       │
                │                               │                       │
                └───────────────┬───────────────┘                       │
                                ▼                                       │
                     ┌────────────────────┐                             │
        exit 2  ◄────┤   what happened?   ├────►  exit 0                │
        BLOCKED      └────────────────────┘       PROCEEDS ─────────────┘
     reason printed            │                                        │
     to the agent              │  anything else (crash, timeout)        ▼
                               └──►  hook ERROR — tool STILL PROCEEDS   │
                                                                        ▼
                                             PostToolUse → audit.log (append-only)
```

**Only exit 2 blocks.** Every other outcome silently allows — that one fact drives the
whole design. It is why the gate must never crash, and why the exit code, not the
reasoning, is the control.

Three consequences worth naming, all in `permission.py`:

- **Bad input denies.** Empty stdin, malformed JSON and a wrong payload shape all exit 2
  (the `_deny(...)` calls in CLI mode) rather than erroring out.
- **Untrusted policy denies.** A policy file that exists but will not parse raises
  `PolicyError`, which CLI mode converts to exit 2. Before that, a `JSONDecodeError`
  escaped as exit 1 — a *non-blocking* hook error — so one corrupt JSON file disabled
  both hard-deny gates, S2.4 included.
- **Unknown tools deny.** `check_phase_gate` ends in `return f"{tool_name} not in
  allowlist"`, so a tool nobody approved is refused rather than waved through.

Gate ①a runs **before** the command patterns on purpose: it has a built-in floor
(`BUILTIN_PROTECTED_PATHS`) and so still returns a verdict when policy is unreadable,
whereas the deny-list has nothing to fall back on.

> Citations here name **functions and constants, not line numbers** — deliberately. The
> previous revision cited `:32/:66/:99`, and every one of those anchors broke the moment
> Gate 1a was inserted above them. Names survive edits; line numbers rot silently.

### The tailoring path (build-time, human-reviewed)

The two paths meet at a **file**, not at a function call. The model writes it once; the
mechanism reads it thereafter.

```
  Context/*.md          /security-tailor          coverage.json        check_coverage.py
  ────────────          ────────────────          ─────────────        ─────────────────
  product design   ──►  a MODEL reads and    ──►  which controls  ──►  every "applies"
  AI stack              classifies                apply to THIS         control maps to a
  deployment target     (proposes only)           product              control-matrix.md
  scope                        │                                       row with a real
                               │                                       Verification
                               ▼                                              │
                    active-controls.md                                        ▼
                    loaded EVERY session                                  ./init.sh
                    via CLAUDE.md                                     exit ≠ 0 → blocked
                               │
                               ▼
                    ┌─────────────────────────────────────────────┐
                    │  A model may only decide things a human     │
                    │  reviews BEFORE they take effect.           │
                    └─────────────────────────────────────────────┘
```

The gate enforces **completeness** (a verification is mapped), not **adequacy** (that it
is a good check). Adequacy stays with human review and sign-off.

### What is actually mechanical — and what is not

Honest status, as of this commit. "Mechanical" means an execution path enforces it **and**
a test proves that path.

| Layer | Where | Status |
|---|---|---|
| Control plane, dev-time | `governance/permission.py` via PreToolUse | **Mechanical.** Wired in `.claude/settings.json`, proven by `tests/test_hooks.py`, gated in `init.sh` block 5b |
| Self-protection (S2.4) | `check_protected_paths` (Gate ①a) | **Mechanical.** Blocks writes to the mechanism and policy by *file identity* — traversal, absolute, symlink, hard-link and case-variant forms all collapse to the same target (`os.path.samefile`, so identity not spelling). Additive-only policy: `BUILTIN_PROTECTED_PATHS` holds even if the policy key is emptied or deleted. Proven by `tests/test_protected_paths.py`. **One open vector of those tested:** an interpreter one-liner (`python3 -c open(...,'w')`), documented in `SECURITY.md` S2.4 and pinned by a test so it cannot close silently without the doc changing |
| Credential block, dev-time | `Security-kit/secret_scan.py` | **Mechanical.** Wired in `.claude/settings.json` |
| Coverage completeness | `check_coverage.py` inside `./init.sh` | **Mechanical, and currently failing closed** — no `coverage.json` on disk yet, so it exits 1 until `/security-tailor` runs |
| Audit trail | `Harness-Best-Practice/observability/audit_hook.py` | **Mechanical** for observation only — PostToolUse cannot veto |
| Data plane | `Security-kit/content_trust.py` | **Library only.** Referenced from `tests/` and nowhere else — no ingestion path calls it |
| Tool coverage | the `matcher` in `.claude/settings.json` | **Gap.** It lists five tools; anything outside it (`WebFetch`, MCP writes, subagent spawns, scheduled jobs) reaches no gate. Gate ①a *would* judge an MCP write carrying a `path`, but the matcher never invokes it |
| Prompt-entry gate | — | **Gap.** No `UserPromptSubmit` hook exists anywhere in this repo |
| Runtime enforcement | `Security-kit/runtime/` | **Does not exist.** Design only — see `docs/superpowers/specs/2026-08-04-runtime-tool-mediation-design.md` |

Two boundaries worth stating plainly:

- **`demo/` is not the production path.** It is scripted evaluation infrastructure
  (`demo/ARCHITECTURE.md:3`). The real path is `.claude/settings.json` hooks →
  `governance/permission.py` CLI mode (`demo/ARCHITECTURE.md:29`).
- **Dev-time ≠ runtime.** A dev-time hook is a *subscription to Claude Code's event loop*
  — JSON on stdin, exit 2 to block. A deployed agent (LangChain, Strands, a plain loop)
  has no hook system; there, enforcement is a function you wrote calling another function
  you wrote. The kit ships the first today; the second is specified, not built.

---

The Security Kit is the template's security navigation and review layer. It does not
replace the existing policy, enforcement, or test assets; it connects them to
project-specific controls and review evidence.

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
