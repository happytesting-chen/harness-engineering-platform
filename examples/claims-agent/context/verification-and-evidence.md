# Build A Verification and Evidence Contract

## Scope and fixture quality
Builds A and B use committed synthetic JSON fixtures only. Never copy production claims, names, addresses, policy numbers, credentials, secrets, URLs, email addresses, or free text that could be interpreted as instructions. Fixture identifiers must be visibly synthetic (`SYN-*`), stable, unique, reviewable, and small enough to understand without external context.

Future fixtures must conform to this versioned shape; `expected` is a test oracle and must not be supplied to decision logic:

```json
{
  "schema_version": "1.0",
  "fixture_id": "SYN-FIXTURE-001",
  "claim": {
    "claim_id": "SYN-CLAIM-001",
    "submitted_amount": "125.00",
    "covered_amount": "125.00",
    "currency": "USD",
    "documentation_complete": true,
    "trusted": true,
    "safety_flags": []
  },
  "expected": {"outcome": "APPROVED", "reason_code": "EXACT_COVERAGE"}
}
```

Amounts are non-negative canonical decimal strings with exactly two fractional digits; floating-point values are invalid. Currency is an uppercase three-letter code. Booleans are JSON booleans, safety flags are unique strings, unknown fields are rejected, and outcome is one of `APPROVED`, `REJECTED`, or `PENDING_REVIEW`. Missing, malformed, unknown, insufficient, unsafe, or untrusted data must never be approved. The later fixture set must cover each terminal outcome plus malformed, boundary, duplicate-write, and failed-write cases; this task creates no fixtures.

## Reviewed verification commands
Run from `examples/claims-agent/` with no network or credentials:

- Unchanged retained Core Harness tests: `python3 -m pytest tests -v`
- Future Claims-only tests: `python3 -m pytest claims/tests -v`
- Complete Build A verification after Claims tests exist: `python3 -m pytest tests claims/tests -v`

Do not alter retained core tests to obtain a pass. Record the exact command, UTC timestamp, repository revision when available, exit code, passed/failed/error counts, and relevant test names. Re-run the complete command unchanged to support reproducibility; any skipped, deselected, flaky, or environment-dependent result is a gap unless explicitly reviewed.

## Evidence and fail-closed handling
Evidence must be attributable to a command or human review, non-sensitive, and stored only in the designated local evaluation packet. Retain concise summaries or hashes rather than fixture payload copies, environment dumps, prompts, credentials, raw model content, or personal data. Distinguish policy intent, observed behavior, and mechanically enforced behavior; documentation or configuration alone does not prove runtime prevention.

A result passes only when exactly one minimal local result is written successfully inside the approved local boundary and matches the deterministic terminal outcome. An absent, partial, failed, duplicate, conflicting, non-minimal, or out-of-bound write fails closed: withhold fixture success and all dependent score/pass claims, preserve non-sensitive failure evidence, and route the case to `PENDING_REVIEW` or `REJECTED` as the implemented contract permits. Never retry by invoking an LLM, network, credential, cloud, email, or external action. Any prohibited-action attempt, incomplete evidence, policy ambiguity, or verification failure blocks readiness until a human reviews resolution and verification is rerun.
