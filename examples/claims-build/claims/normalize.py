"""Stage 2 — Normalize.

Produce canonical deterministic values without inventing missing meaning.
Monetary values become exact ``Decimal`` (from the validated two-fraction-digit
strings) so comparison is exact, never binary-float approximation.

Input is assumed already validated (claims.validate.validate). Normalization
does not decide anything; it only canonicalizes.
"""

from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple


class NormalizedClaim(NamedTuple):
    """Canonical, immutable view used solely by the router."""

    claim_id: str
    submitted_amount: Decimal
    covered_amount: Decimal
    currency: str
    documentation_complete: bool
    trusted: bool
    safety_flags: tuple[str, ...]


def normalize(claim: dict) -> NormalizedClaim:
    """Map a validated ``claim`` dict to a NormalizedClaim.

    Amount strings are already constrained to ``^\\d+\\.\\d{2}$`` by validation,
    so Decimal() is exact and total. Safety flags become a sorted tuple for
    deterministic ordering across runs.
    """
    return NormalizedClaim(
        claim_id=claim["claim_id"],
        submitted_amount=Decimal(claim["submitted_amount"]),
        covered_amount=Decimal(claim["covered_amount"]),
        currency=claim["currency"],
        documentation_complete=claim["documentation_complete"],
        trusted=claim["trusted"],
        safety_flags=tuple(sorted(claim["safety_flags"])),
    )
