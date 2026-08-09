# Security Control Matrix

Complete only the rows that apply to the copied project's approved design. The matrix links a security objective to its implementation, verification, and review evidence.

| Control ID | Objective and boundary | Implementation location | Verification | Review evidence |
|---|---|---|---|---|
| `SEC-TOOL-001` | Only approved tools may execute; `claims_runner` stays locked until phase-01 is human-signed to passing | `governance/mcp-allowlist.json` (`gated_until: phase-01`) | `python3 tests/test_fixtures.py` (Case #3 phase-gate) | Tool/version approval; phase sign-off record |
| `SEC-EGRESS-001` | No outbound network; `egress_hosts` is empty so every destination is denied | `governance/mcp-allowlist.json` (`egress_hosts: []`), `governance/permission.py` | `python3 tests/test_fixtures.py` (Case #4 egress deny) | Egress policy review (default-deny, no host approved) |
| `SEC-DENY-001` | Prohibited effects (LLM/provider, cloud, network exfil, email) are blocked regardless of phase or wording | `governance/deny-list.json` (word/regex: curl, wget, ssh, scp, aws, gcloud, openai, anthropic, sendmail) | `python3 tests/test_fixtures.py` (Case #1, #6 deny-list) | Deny-list review vs. claims hard constraints |
| `SEC-DATA-001` | Fixture text is untrusted data — never instruction, prompt, approval, or tool authority | `Security-kit/content_trust.py` | `python3 tests/test_content_trust.py` | Data-plane boundary review |
| `SEC-HOOK-001` | Every wired hook script resolves on disk; a missing path (config error) is distinguished from a policy BLOCK before it fail-closes every tool | `.claude/settings.json`, `init.sh` check (e) | `./init.sh` (`✓ all wired hook paths resolve on disk`) | Negative test: hidden `permission.py` → `✗ GATE MISCONFIGURED` |

## Completion Rules

- Use stable IDs so features, tests, and review records can reference the same control.
- Add a row when a feature introduces or changes a trust boundary, tool, external service, identity rule, sensitive data flow, or deployment control.
- Link evidence; do not claim that a control is enforced without a mapped verification.
