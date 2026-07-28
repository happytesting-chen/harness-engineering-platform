# Red Team Agent Harness — Demo Repo

A runnable example of Harness Engineering applied to a security use case.
Backs slides 9/11/13 of the CTO deck with real, executable code.

## What this proves

The same harness-engineering principles (Customise → Operationalise → Secure)
applied to one concrete agent type: an authorized Red Team agent running a
penetration test engagement.

## Repository structure

```
red-team-harness/
├── AGENTS.md                    → Entry point · Context layer
├── feature_list.json            → Phase DAG: scope→recon→exploit→report
├── init.sh                      → Startup verification
├── progress.md                  → Session continuity log
│
├── context/                     → CUSTOMISE: what the agent knows
│   ├── attck-layer.json         → Pinned ATT&CK Navigator layer (subset)
│   ├── target-scope.md          → Authorized IP ranges, time window
│   └── methodology.md           → Recon→Exploit→Escalate→Report workflow
│
├── tools/                       → CUSTOMISE: what the agent can use
│   ├── mcp-allowlist.json       → Permitted MCP servers (nmap, burp; metasploit gated)
│   └── tool-registry.md         → Version pins + review status per tool
│
├── governance/                  → CUSTOMISE + SECURE: boundaries
│   ├── permission.py            → Permission gate (deny-list + egress + phase gate)
│   ├── deny-list.json           → Hard-deny: no DoS, no lateral beyond ROE
│   └── phase-gate.py            → Enforces feature_list.json DAG
│
├── observability/               → Shared: audit trail
│   ├── audit.py                 → Append-only JSON log
│   └── audit.log                → Generated at runtime
│
├── harness.py                   → The agent loop
├── demo.py                      → Scripted engagement demo (see below)
│
├── tests/
│   ├── test_permission.py       → Unit: deny-list rules
│   ├── test_phase_gate.py       → Unit: phase DAG enforcement
│   └── test_harness_e2e.py      → E2E: full pipeline enforcement
│
└── README.md                    → This file
```

## How to run (once code is filled in)

```bash
# 1. See the harness enforce phase gating
python3 demo.py

# Expected output:
#   ✓ allow   nmap -sV 10.20.0.0/24     (Phase 1: recon, in scope)
#   ⛔ DENIED  msfconsole ...             (Phase 2 not signed off yet)
#   [human approves Phase 1 → Phase 2 unlocks]
#   ✓ allow   msfconsole ...             (now permitted)

# 2. Run all verification
pytest tests/

# 3. Verify the harness catches a deliberate bypass
#    (same break-then-fix pattern from harness-lab Day 4)
```

## How each file maps to the deck (CTO v2)

| Deck slide | Repo files | What it demonstrates |
|---|---|---|
| Slide 9 (Customise) | `context/`, `tools/`, `governance/deny-list.json` | What the domain expert fills in before day 1 |
| Slide 11 (Operationalise) | `demo.py` + `feature_list.json` phase transitions | One real session: init→recon→verify→clean exit |
| Slide 13 (Secure) | `tests/test_harness_e2e.py` + `governance/phase-gate.py` | Each threat from the slide has a test that tries to break the control |
| Slide 14 (Design→Enforce→Verify) | `governance/` = design+enforce, `tests/` = verify | The three-step lifecycle per control |

## Current status

**Scaffold only.** File structure and this README created. Code not yet filled in.
Next step: implement `harness.py` + `governance/permission.py` + `demo.py` as the
first working slice (same pattern as harness-lab/, extended with phase gating).

## Relationship to harness-lab/

`harness-lab/` is the general teaching repo (one permission gate, generic tools).
This repo is the *domain-specific instance* — the same foundational pattern,
filled with pentesting-specific content (ATT&CK references, phase-gated tools,
ROE-based scope enforcement). It's what happens when a domain expert fills in
the customisation layer for their use case.
