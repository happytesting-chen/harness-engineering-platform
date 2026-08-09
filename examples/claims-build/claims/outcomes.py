"""Terminal outcomes and the immutable result envelope.

Three terminal outcomes only (Context/claims-architecture.md). There is no
permissive fallback: unsafe ambiguity resolves to PENDING_REVIEW, never APPROVED.
"""

from __future__ import annotations

from typing import NamedTuple

APPROVED = "APPROVED"
REJECTED = "REJECTED"
PENDING_REVIEW = "PENDING_REVIEW"

TERMINAL_OUTCOMES = (APPROVED, REJECTED, PENDING_REVIEW)


class Outcome(NamedTuple):
    """A routing decision: exactly one terminal outcome plus a stable reason.

    Immutable by construction (NamedTuple). ``claim_id`` is the minimum
    attributable identifier; it is ``None`` only when the input was too
    malformed to surface a trustworthy id.
    """

    outcome: str
    reason_code: str
    claim_id: str | None


def is_terminal(outcome: str) -> bool:
    return outcome in TERMINAL_OUTCOMES
