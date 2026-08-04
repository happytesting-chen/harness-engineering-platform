"""process_email — the Build C front-end orchestrator.

    raw email text
        -> extractor.extract()      (UNTRUSTED proposal; LLM or FakeExtractor)
        -> assemble record          (covered_amount OVERRIDDEN from policy store)
        -> claims.decide()          (UNCHANGED deterministic core; sole authority)
        -> Outcome

Design invariants (each enforced below, not just documented):
  1. The extractor never decides. It only proposes fields.
  2. covered_amount and currency come from the TRUSTED policy store, never the
     email — so a plausibly-lying extractor cannot fabricate an approval.
  3. Any malformed extractor output falls through to the existing validate()
     gate and becomes PENDING_REVIEW — the front-end adds no permissive path.
  4. An unknown claim_id (no trusted policy) is PENDING_REVIEW, never decided.
"""
from __future__ import annotations

from claims.outcomes import PENDING_REVIEW, Outcome
from claims.pipeline import decide

from .model import Extractor
from .policy_store import PolicyNotFound, lookup_coverage


def _proposed_claim_id(proposal: object) -> str | None:
    """Best-effort id from an untrusted proposal, for attribution only."""
    if isinstance(proposal, dict):
        claim = proposal.get("claim")
        if isinstance(claim, dict):
            cid = claim.get("claim_id")
            if isinstance(cid, str) and cid:
                return cid
    return None


def process_email(email_text: str, extractor: Extractor) -> Outcome:
    """Extract a claim from email, price it from trusted policy, then decide.

    Returns exactly one Outcome. No side effects (no write). The caller may pass
    the result to claims.writer separately if a persisted result is wanted.
    """
    proposal = extractor.extract(email_text)  # UNTRUSTED
    cid = _proposed_claim_id(proposal)

    # Guard the shape enough to reach the trusted lookup; anything odd -> review.
    if not isinstance(proposal, dict) or not isinstance(proposal.get("claim"), dict):
        return Outcome(PENDING_REVIEW, "MALFORMED_EXTRACTION", cid)

    proposed_claim = proposal["claim"]

    # Price from the TRUSTED store, keyed by the proposed id. Unknown -> review.
    try:
        coverage = lookup_coverage(cid)
    except PolicyNotFound:
        return Outcome(PENDING_REVIEW, "POLICY_NOT_FOUND", cid)

    # Copy the untrusted proposal, then OVERRIDE covered_amount + currency from
    # the trusted policy. The email can never set coverage. We do NOT filter the
    # proposal's other keys: the unchanged validate() enforces the exact field
    # set, so a hallucinated field becomes UNKNOWN_FIELD -> PENDING_REVIEW and a
    # missing field becomes MISSING_REQUIRED_FIELD -> PENDING_REVIEW. The
    # front-end adds no permissive path; it only pins the numbers it controls.
    claim = dict(proposed_claim)
    claim["covered_amount"] = coverage["covered_amount"]  # trusted override
    claim["currency"] = coverage["currency"]              # trusted override

    record = {"schema_version": "1.0", "claim": claim}

    # Deterministic core — sole decision authority, unchanged.
    return decide(record)
