# Security Control Matrix

Complete only the rows that apply to the copied project's approved design. The matrix links a security objective to its implementation, verification, and review evidence.

| Control ID | Objective and boundary | Implementation location | Verification | Review evidence |
|---|---|---|---|---|
| `SEC-TOOL-001` | Only approved tools may execute | `governance/mcp-allowlist.json` | `python3 tests/test_fixtures.py` | Tool/version approval |
| `SEC-EGRESS-001` | Network actions stay within approved destinations | `governance/mcp-allowlist.json`, `governance/permission.py` | Egress fixture or E2E test | Egress policy review |
| `SEC-XXX-001` | {{PROJECT_SPECIFIC_SECURITY_OBJECTIVE}} | {{IMPLEMENTATION_LOCATION}} | {{VERIFICATION_COMMAND}} | {{REVIEW_RECORD_OR_DECISION}} |

## Completion Rules

- Use stable IDs so features, tests, and review records can reference the same control.
- Add a row when a feature introduces or changes a trust boundary, tool, external service, identity rule, sensitive data flow, or deployment control.
- Link evidence; do not claim that a control is enforced without a mapped verification.
