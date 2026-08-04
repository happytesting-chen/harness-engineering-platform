"""Trusted policy store — the authoritative source of coverage amounts.

THE case-5 mitigation. The seam probe showed the deterministic core cannot catch
an extractor that lies *plausibly* about the numbers (e.g. reports
covered == submitted when the truth is a shortfall). So the covered amount is
never taken from the email at all: it is looked up here, keyed by claim_id, from
a trusted record the extractor cannot influence. The LLM cannot move a number it
does not control.

Stub build: an in-memory synthetic table of SYN-* policies. In production this
would be a read against the policy system of record (still not the email).
"""
from __future__ import annotations


class PolicyNotFound(Exception):
    """Raised when a claim_id has no matching trusted policy record."""

    def __init__(self, claim_id: str | None) -> None:
        super().__init__(claim_id or "<unknown>")
        self.claim_id = claim_id


# Synthetic, committed, non-sensitive. covered_amount is the TRUSTED truth.
# Two-fraction-digit strings so they pass claims.validate unchanged.
_POLICIES: dict[str, dict] = {
    "SYN-CLAIM-001": {"covered_amount": "125.00", "currency": "USD"},
    "SYN-CLAIM-101": {"covered_amount": "480.00", "currency": "USD"},  # full coverage
    "SYN-CLAIM-102": {"covered_amount": "10.00", "currency": "USD"},   # real shortfall
    "SYN-CLAIM-103": {"covered_amount": "500.00", "currency": "USD"},  # anomaly (> submitted)
}


def lookup_coverage(claim_id: str | None) -> dict:
    """Return the trusted {covered_amount, currency} for a claim_id.

    Raises PolicyNotFound if the id is unknown — a claim we cannot price against
    a trusted policy is a review case, never an auto-decision.
    """
    if not isinstance(claim_id, str) or claim_id not in _POLICIES:
        raise PolicyNotFound(claim_id if isinstance(claim_id, str) else None)
    return dict(_POLICIES[claim_id])  # copy — callers never mutate the store
