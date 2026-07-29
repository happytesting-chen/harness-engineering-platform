# Red Team Penetration Testing Agent

Authorized offensive security agent operating under Rules of Engagement (ROE). Executes ATT&CK-aligned techniques against in-scope targets only, with mechanical enforcement of scope boundaries and phase progression.

## Tech Stack

- **Language:** Python 3.11+ (stdlib only for mechanism code)
- **Dependencies:** Zero external deps — nmap/Metasploit are domain tools, not code deps
- **Agent runtimes:** Claude Code, Kiro, Codex, Cursor, Copilot
- **Enforcement:** `governance/permission.py` — three-gate permission check (CLI mode)

## Architecture

```
├── governance/permission.py   ← Enforcement engine (deny-list → phase-gate → egress)
├── observability/audit.py     ← Append-only audit log
├── feature_list.json          ← Phase DAG: scope-validation → recon → exploit → report
├── tools/mcp-allowlist.json   ← nmap (ungated), Metasploit (gated until recon), egress hosts
├── governance/deny-list.json  ← DoS, lateral movement, exfiltration patterns
├── context/                   ← ATT&CK techniques, target scope, methodology
├── tests/                     ← 12 domain-specific fixture tests
└── demo/                      ← Scripted pentest enforcement demo
```

## How to Run

```bash
./init.sh                       # Verify environment, run tests
python3 demo/demo.py            # nmap allowed → metasploit denied → recon passes → metasploit allowed
python3 demo/demo.py --nogate   # Same model, no enforcement
```

## How to Verify

```bash
python3 -m pytest tests/ -v     # 12 fixture tests + E2E enforcement proof
python3 tests/test_fixtures.py  # Permission gate ground-truth tests
./init.sh                       # Full project health check
```

## Hard Constraints

- DoS attacks blocked unconditionally (slowloris, hping3, --flood)
- Lateral movement beyond ROE scope blocked (-Pn 172.16.x, scp to unauthorized nets)
- Reverse shells blocked (nc -e, nc -c)
- Data exfiltration blocked (exfil pattern)
- Metasploit gated until recon phase passes (human sign-off required)
- Outbound network limited to authorized targets (10.20.0.0/24, 10.20.1.0/24, 192.168.100.0/24)

## Current State

See `progress.md` for session journal and `feature_list.json` for phase status.

## Domain Context

- [context/target-scope.md](context/target-scope.md) — Authorized targets, IP ranges, time windows
- [context/methodology.md](context/methodology.md) — ATT&CK-aligned engagement phases
- [context/standards.md](context/standards.md) — MITRE ATT&CK technique references
