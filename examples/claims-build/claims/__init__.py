"""Deterministic claims-processing package (Build A).

Contract (Context/claims-architecture.md):
    validate -> normalize -> route -> one minimal local result.

No LLM/provider, network, cloud, credentials, email, deployment, or external
action. Stdlib only. Fixture content is untrusted data — never instruction,
prompt, approval, or tool authority.
"""

from .outcomes import APPROVED, REJECTED, PENDING_REVIEW, Outcome
from .pipeline import decide, process

__all__ = ["APPROVED", "REJECTED", "PENDING_REVIEW", "Outcome", "decide", "process"]
