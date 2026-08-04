# Security Kit

The Security Kit is the template's security navigation and review layer. It does not replace the existing policy, enforcement, or test assets; it connects them to project-specific controls and review evidence.

## Use It

1. Follow the baseline guidance in [`SECURITY.md`](SECURITY.md) during development.
2. Fill [`control-matrix.md`](control-matrix.md) with the controls selected for the copied project.
3. Map risks to mechanisms with [`owasp-crosswalk.md`](owasp-crosswalk.md); see [`SECURITY-MANIFEST.md`](SECURITY-MANIFEST.md) for what is security vs domain.
4. For a security-sensitive change, manually include [`kiro/steering/security-review.md`](../kiro/steering/security-review.md) in Kiro before sign-off.
4. Record review evidence in the control matrix and the project handoff or approved review record.

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
