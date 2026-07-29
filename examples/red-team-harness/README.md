# Red Team Harness — Filled Example

A complete instance of the Harness Engineering Platform configured for authorized penetration testing. All `{{placeholders}}` from the template have been filled with pentesting-specific content.

## What This Demonstrates

- **Phase DAG:** scope-validation → recon → exploit → report
- **Phase-gated tools:** Metasploit is locked until recon phase passes
- **Deny-list:** DoS attacks, lateral movement beyond ROE, reverse shells
- **Egress control:** Only authorized target networks (10.20.x.x) permitted
- **ATT&CK alignment:** Techniques mapped to MITRE framework

## Running

```bash
# Run the enforcement demo
python3 demo/demo.py

# Same model, no enforcement (proves the harness matters)
python3 demo/demo.py --nogate

# Run fixture tests
python3 tests/test_fixtures.py

# Run verification
./init.sh
```

## Key Files (domain-specific content)

- `CLAUDE.md` — Red Team agent instructions with ROE references
- `feature_list.json` — 4-phase engagement DAG
- `governance/deny-list.json` — DoS, lateral movement, exfiltration patterns
- `tools/mcp-allowlist.json` — nmap (ungated), Metasploit (gated until recon)
- `context/target-scope.md` — Authorized IP ranges and time windows
- `context/methodology.md` — ATT&CK-aligned engagement phases
- `context/standards.md` — MITRE technique references
