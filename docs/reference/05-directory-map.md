# Directory map of the template

```
my-agent/
├── CLAUDE.md              ← Claude Code instructions (imports @AGENTS.md)   [FILL]
├── README.md             ← This file                                       [as-is]
├── init.sh               ← Startup health check + integrity gate           [as-is]
├── install.sh            ← Build assembler (full / --no-security)          [as-is]
│
├── governance/            ← ENFORCEMENT + POLICY (top-level)
│   ├── permission.py      ← [MECHANISM] 4-gate control plane                [never edit]
│   ├── runtime_dispatcher.py ← [MECHANISM] ②③④ for a DEPLOYED app          [never edit]
│   ├── deny-list.json     ← [POLICY] hard-blocked patterns                  [EXTEND]
│   └── mcp-allowlist.json ← [POLICY] approved tools + egress hosts          [FILL]
│
├── Security-kit/          ← SECURITY KIT (generic, not domain-specific)
│   ├── README.md
│   ├── SECURITY.md         ·  42-control reference (source-tagged, S1.1–S8.6)
│   ├── owasp-crosswalk.md  ·  OWASP LLM/Agentic → mechanism map
│   ├── SECURITY-MANIFEST.md·  what is security vs non-security
│   ├── control-matrix.md   ·  control → code → test → evidence             [FILL rows]
│   ├── coverage.schema.md  ·  the shape /security-tailor must produce
│   ├── coverage.json       ·  which OWASP ids apply here    [WRITTEN by /security-tailor]
│   ├── active-controls.md  ·  the applicable subset, @-imported by CLAUDE.md [GENERATED]
│   ├── requirements.json   ·  obligation spine (SEC-REQ-001…011)      [human-owned]
│   ├── mechanisms.json     ·  claims register: what actually EXISTS    [human-owned]
│   ├── check_coverage.py   ← [MECHANISM] coverage gate + invariants I1–I6  [never edit]
│   ├── content_trust.py    ← [MECHANISM] shared marker list (data plane)    [never edit]
│   ├── prompt_screen.py    ← [MECHANISM] ① UserPromptSubmit screen          [never edit]
│   ├── result_screen.py    ← [MECHANISM] ④ PostToolUse result screen        [never edit]
│   ├── runtime_screen.py   ← [MECHANISM] ①④ for a DEPLOYED app, regex tier   [never edit]
│   └── runtime/            ← [MECHANISM] the runtime-mvp semantic tier (16 modules) [never edit]
│       ├── host.py         ·  the owned loop — the one entry point a deployed app calls
│       ├── ingress.py      ·  ①④ decision table: rules + classifier → ALLOW | REQUIRE_REVIEW
│       ├── guarded.py, session.py · ⑤ session ceilings, origin rules, schema — composed around ②
│       ├── review.py       ·  content-release and action-approval receipts (typed, keyed)
│       ├── classifier.py   ·  pinned local classifier protocol; semantic-model.lock.json
│       └── audit.py, output.py, startup.py · hash-chained evidence, buffered output, refuse-to-start
│   ├── secret_scan.py      ← [MECHANISM] secret-block hook adapter          [never edit]
│   └── eval/               ·  labelled corpora + scorers; runtime_injection/ (40-case benchmark corpus); bootstrap_classifier.py
│
├── Harness-Best-Practice/ ← IDENTITY + WORKFLOW STATE
│   ├── AGENTS.md          ← Open standard: identity, run/verify             [FILL]
│   ├── progress.md        ← Session journal + handoff                       [UPDATE]
│   ├── feature_list.json  ← Phases: behavior + verification + status        [FILL]
│   ├── BEST-PRACTICES.md  ← Harness engineering principles (generic)        [as-is]
│   └── observability/
│       ├── audit.py       ← [MECHANISM] append-only audit log               [never edit]
│       └── audit_hook.py  ← [MECHANISM] PostToolUse audit adapter           [never edit]
│
├── tests/                 ← VERIFICATION (38 suites, 339 tests; all stdlib, pytest optional)
│   ├── fixtures.json          ·  ground-truth gate cases                    [EXTEND]
│   ├── test_fixtures.py       ·  data-driven gate runner
│   ├── test_e2e.py            ·  end-to-end enforcement proof
│   ├── test_hooks.py          ·  hook-script contract (envelope on stdin → exit code)
│   ├── test_content_trust.py  ·  data-plane boundary proof
│   ├── test_prompt_screen.py  ·  ① prompt screen
│   ├── test_result_screen.py  ·  ④ result screen + updatedToolOutput shape
│   ├── test_result_screening.py· ④ in-loop proof: the bytes never reach `messages`
│   ├── test_injection_corpus.py· pins 10/12 caught + 2/12 false positives
│   ├── test_protected_paths.py·  S2.4 self-modification proof + pinned gaps
│   ├── test_shipped_policy.py ·  the real deny-list.json, both directions
│   ├── test_coverage.py       ·  the coverage gate itself (fail-closed, staleness)
│   ├── test_mechanisms.py     ·  claims-register census + invariants I1–I5
│   ├── test_requirements.py   ·  requirement spine ↔ controls (I6)
│   ├── test_eval_selection.py ·  the scorer behind Security-kit/eval/
│   ├── test_steady_state.py   ·  availability + no self-promotion via the worklog
│   ├── test_egress.py         ·  Gate 3: exact host match + structured destinations
│   ├── test_runtime_dispatcher.py· ②③④ in process; `calls == 0` proves prevention
│   ├── test_runtime_screen.py ·  ①④ in process; ① fails closed on unscannable input
│   └── runtime/           ·  18 suites for the semantic tier — ingress table, receipts,
│                             ceilings under concurrency, attack replay, claims truthfulness
│
├── Context/               ← [POLICY] PROJECT AI-dev assets                   [FILL stubs]
│   ├── README.md           ·  what belongs here
│   ├── ai-stack.md.template     ·  framework + model choice        [copy→fill]
│   └── deployment.md.template   ·  on-prem/cloud, egress, secrets  [copy→fill]
│
├── demo/                  ← DEMONSTRATION (not the production path)
│   ├── harness.py · demo.py · fake_model.py   (zero-dependency LLM mock)
│
├── evaluation/            ← MEASUREMENT — the third proof after tests/ and demo/
│   ├── runtime-security/  ·  attack traces, replay, classifier selection, limitations, VERDICT.md
│   ├── eval.py            ·  accuracy / cost / reproducibility metrics (run by init.sh)
│   ├── SNAPSHOT.template.md ·  filled by `eval.py --snapshot DIR` for sign-off
│   └── README.md
│
├── .claude/               ← CLAUDE CODE (active runtime)
│   ├── settings.json      ← hooks: prompt-screen ① · governance-check · secret-block
│   │                        · result-screen ④ · audit-capture · clean-state   [never edit]
│   └── commands/          ← /init-project · /security-tailor · /session-cycle · /domain-workflow
│
└── kiro/                  ← KIRO ADD-ON (opt-in: `cp -r kiro/ .kiro/` to activate)
    ├── README.md
    ├── hooks/             ← governance · secret-block · audit · clean-state
    └── steering/          ← session-cycle · domain-workflow · security · security-review
                             · security-tailor · active-controls
```

Every module also carries an `ARCHITECTURE.md` describing its role.

---
