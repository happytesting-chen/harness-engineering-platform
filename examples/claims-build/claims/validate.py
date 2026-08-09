"""Stage 1 — Validate.

Verify input shape, required values, types, and allowed state BEFORE any
decision is attempted. This stage never executes or follows fixture text; it
only inspects structure. Any structural defect is reported as a reason string
(the router turns it into PENDING_REVIEW) — validation never itself approves.

The fixture ``expected`` block is a test oracle: it is intentionally NOT read
here and must never reach normalization or routing.
"""

from __future__ import annotations

import re
from typing import Any

# Canonical wire shape (Context/verification-and-evidence.md).
_ALLOWED_TOP_LEVEL = {"schema_version", "fixture_id", "claim", "expected"}
_REQUIRED_TOP_LEVEL = {"schema_version", "claim"}
_ALLOWED_CLAIM_FIELDS = {
    "claim_id",
    "submitted_amount",
    "covered_amount",
    "currency",
    "documentation_complete",
    "trusted",
    "safety_flags",
}
_SUPPORTED_SCHEMA_VERSIONS = {"1.0"}

# Non-negative decimal string with exactly two fractional digits. Floats are invalid.
_AMOUNT_RE = re.compile(r"^\d+\.\d{2}$")
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


class ValidationDefect(Exception):
    """Raised when the input cannot be trusted as a well-formed claim.

    Carries a stable ``reason_code`` and the best-effort ``claim_id`` (may be
    None). The pipeline converts this into a PENDING_REVIEW outcome — a defect
    is never REJECTED, because "malformed/unknown" is a review case, not a
    definitively-invalid business decision.
    """

    def __init__(self, reason_code: str, claim_id: str | None = None) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.claim_id = claim_id


def _safe_claim_id(record: Any) -> str | None:
    """Best-effort id extraction for evidence, without trusting the value."""
    if isinstance(record, dict):
        claim = record.get("claim")
        if isinstance(claim, dict):
            cid = claim.get("claim_id")
            if isinstance(cid, str) and cid:
                return cid
    return None


def validate(record: Any) -> dict:
    """Return the trusted ``claim`` sub-dict, or raise ValidationDefect.

    Unknown fields at either level are rejected (fail-closed against silently
    ignoring meaning). ``expected`` is permitted at the top level but is not
    returned — decision logic never sees the oracle.
    """
    cid = _safe_claim_id(record)

    if not isinstance(record, dict):
        raise ValidationDefect("MALFORMED_RECORD", None)

    unknown_top = set(record) - _ALLOWED_TOP_LEVEL
    if unknown_top:
        raise ValidationDefect("UNKNOWN_FIELD", cid)
    if not _REQUIRED_TOP_LEVEL.issubset(record):
        raise ValidationDefect("MISSING_REQUIRED_FIELD", cid)
    if record.get("schema_version") not in _SUPPORTED_SCHEMA_VERSIONS:
        raise ValidationDefect("UNSUPPORTED_SCHEMA_VERSION", cid)

    claim = record.get("claim")
    if not isinstance(claim, dict):
        raise ValidationDefect("MALFORMED_CLAIM", cid)

    unknown_claim = set(claim) - _ALLOWED_CLAIM_FIELDS
    if unknown_claim:
        raise ValidationDefect("UNKNOWN_FIELD", cid)
    if set(claim) != _ALLOWED_CLAIM_FIELDS:
        raise ValidationDefect("MISSING_REQUIRED_FIELD", cid)

    # Types and formats — exact, no coercion.
    if not isinstance(claim["claim_id"], str) or not claim["claim_id"]:
        raise ValidationDefect("MALFORMED_CLAIM_ID", cid)
    cid = claim["claim_id"]

    for amount_field in ("submitted_amount", "covered_amount"):
        value = claim[amount_field]
        # bool is a subclass of int/str is not — reject non-str and float outright.
        if not isinstance(value, str) or not _AMOUNT_RE.match(value):
            raise ValidationDefect("MALFORMED_AMOUNT", cid)

    if not isinstance(claim["currency"], str) or not _CURRENCY_RE.match(claim["currency"]):
        raise ValidationDefect("MALFORMED_CURRENCY", cid)

    for bool_field in ("documentation_complete", "trusted"):
        if not isinstance(claim[bool_field], bool):
            raise ValidationDefect("MALFORMED_BOOLEAN", cid)

    flags = claim["safety_flags"]
    if not isinstance(flags, list) or not all(isinstance(f, str) and f for f in flags):
        raise ValidationDefect("MALFORMED_SAFETY_FLAGS", cid)
    if len(set(flags)) != len(flags):
        raise ValidationDefect("MALFORMED_SAFETY_FLAGS", cid)

    return claim
