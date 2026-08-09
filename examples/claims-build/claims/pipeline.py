"""Deterministic pipeline: validate -> normalize -> route -> (optional) write.

``process`` returns exactly one Outcome. A structural defect surfaced by
validation is converted to a PENDING_REVIEW outcome (never REJECTED, never
APPROVED) — malformed/unknown/untrusted input is a review case, honoring the
"no permissive fallback" rule.

Unchanged reviewed input yields an equivalent Outcome on every run: the whole
path is pure and stdlib-only, with no clock, randomness, network, or provider.
"""

from __future__ import annotations

from pathlib import Path

from .normalize import normalize
from .outcomes import PENDING_REVIEW, Outcome
from .router import route
from .validate import ValidationDefect, validate
from .writer import write_result


def decide(record: object) -> Outcome:
    """Run validate -> normalize -> route and return one terminal Outcome.

    No side effects. ``record`` is untrusted fixture data and is only inspected.
    """
    try:
        claim = validate(record)
    except ValidationDefect as defect:
        # Structural distrust routes to review, carrying a stable reason and
        # the best-effort claim id for attribution.
        return Outcome(PENDING_REVIEW, defect.reason_code, defect.claim_id)

    normalized = normalize(claim)
    return route(normalized)


def process(record: object, boundary: Path | None = None) -> Outcome:
    """Decide, then optionally emit one minimal local result.

    If ``boundary`` is given, exactly one minimal result file is written inside
    it (fail-closed via claims.writer). If ``boundary`` is None, no write is
    performed and the caller gets the decision only.
    """
    outcome = decide(record)
    if boundary is not None:
        write_result(outcome, boundary)
    return outcome
