"""Stage 3 — Route (sole decision authority).

The deterministic terminal router is the ONLY component that selects an outcome.
No model, fixture, or writer may choose or override the result. Rules are
evaluated in a fixed order; the first match wins. There is no permissive
fallback — anything not definitively APPROVED or REJECTED resolves to
PENDING_REVIEW.

Reviewed Build A rule (Context/claims-architecture.md terminal definitions):

    untrusted                 -> PENDING_REVIEW  (UNTRUSTED)
    any safety flag           -> PENDING_REVIEW  (SAFETY_FLAGGED)
    documentation incomplete  -> PENDING_REVIEW  (INCOMPLETE_DOCUMENTATION)
    covered  < submitted      -> REJECTED        (COVERAGE_SHORTFALL)
    covered  > submitted      -> PENDING_REVIEW  (COVERAGE_ANOMALY)
    covered == submitted      -> APPROVED        (EXACT_COVERAGE)
"""

from __future__ import annotations

from .normalize import NormalizedClaim
from .outcomes import APPROVED, PENDING_REVIEW, REJECTED, Outcome


def route(claim: NormalizedClaim) -> Outcome:
    """Return exactly one terminal Outcome for a normalized claim."""
    # Trust and safety gates come first: an unsafe or untrusted case can never
    # be approved, regardless of the monetary math.
    if not claim.trusted:
        return Outcome(PENDING_REVIEW, "UNTRUSTED", claim.claim_id)
    if claim.safety_flags:
        return Outcome(PENDING_REVIEW, "SAFETY_FLAGGED", claim.claim_id)
    if not claim.documentation_complete:
        return Outcome(PENDING_REVIEW, "INCOMPLETE_DOCUMENTATION", claim.claim_id)

    if claim.covered_amount < claim.submitted_amount:
        return Outcome(REJECTED, "COVERAGE_SHORTFALL", claim.claim_id)
    if claim.covered_amount > claim.submitted_amount:
        # Covered exceeds submitted — anomalous, needs human judgment.
        return Outcome(PENDING_REVIEW, "COVERAGE_ANOMALY", claim.claim_id)

    return Outcome(APPROVED, "EXACT_COVERAGE", claim.claim_id)
