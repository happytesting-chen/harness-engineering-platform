"""runtime-mvp package — the deployed-profile semantic enforcement layer.

Created by the 2026-08-31 re-scoped plan (Task 2 onward). This package holds the
semantic ingress layer and its supporting types. The ACTION plane is deliberately
absent here: gate ② lives in `governance/permission.py` behind
`governance/runtime_dispatcher.py`, and per AD-7 this package composes around that
chokepoint — it never re-implements it. If you find a policy predicate or an action
dispatcher in this package, that is a defect, not a feature.

Profile contract: `Context/runtime-security-profile.md` (test-pinned).
"""
from .contracts import (
    Action,
    ActionApprovalReceipt,
    ContentEnvelope,
    ContentReleaseReceipt,
    IngressDecision,
    IngressOutcome,
    Origin,
)

__all__ = [
    "Action",
    "ActionApprovalReceipt",
    "ContentEnvelope",
    "ContentReleaseReceipt",
    "IngressDecision",
    "IngressOutcome",
    "Origin",
]
