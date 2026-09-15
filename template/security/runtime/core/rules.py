"""The deterministic rule layer — a thin adapter over `content_trust.scan_text` (Task 4).

Two invariants, both test-pinned:

1. **This module owns no pattern.** `content_trust.py` is the single owner of
   `_INJECTION_MARKERS`; this adapter imports `scan_text` and never compiles a
   detection regex of its own. The same anti-drift rule the hook adapters live under
   (`tests/runtime/test_rules.py` scans this file's source for the compile call).
2. **The rule engine never returns `data`.** Its labels are a closed two-value enum:
   `INSTRUCTION` (a marker or escalating structural signal fired) or `UNRESOLVED`
   (nothing fired — which is a handoff to the semantic layer, not a clean bill).

Marker evidence uses stable short digests of the pattern source (`marker:<12 hex>`),
so audit records do not depend on truncated regex strings and survive marker rewording
that preserves semantics. The digest is derived, not stored — `content_trust.py` is a
protected path and needs no edit for this (plan Task 4, as amended).

Stdlib only. Deterministic: no clock, no environment, no I/O.
"""
import hashlib
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# content_trust.py lives one directory up (Security-kit/), beside this package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from content_trust import scan_text  # noqa: E402

from .normalization import NormalizedContent  # noqa: E402


class RuleLabel(str, Enum):
    INSTRUCTION = "instruction"
    UNRESOLVED = "unresolved"
    # deliberately no DATA: absence of a marker is not proof content is safe


@dataclass(frozen=True)
class RulePolicy:
    version: str
    # Whether normalization signals (zero-width, bidi, encoded-span) escalate to
    # INSTRUCTION on their own, or ride as evidence while the label stays UNRESOLVED
    # for the semantic layer to judge. Committed policy, not a runtime toggle.
    structural_signals_escalate: bool = True

    def __post_init__(self):
        if not (isinstance(self.version, str) and self.version.strip()):
            raise ValueError("RulePolicy.version must be a non-blank string")


@dataclass(frozen=True)
class RuleDecision:
    label: RuleLabel
    rule_version: str
    marker_ids: tuple = ()
    signal_ids: tuple = ()


def _marker_id(pattern_source: str) -> str:
    return "marker:" + hashlib.sha256(pattern_source.encode("utf-8")).hexdigest()[:12]


def evaluate_rules(content: NormalizedContent, policy: RulePolicy) -> RuleDecision:
    """Judge normalized text. INSTRUCTION on any marker hit; structural signals
    escalate per committed policy; everything else is UNRESOLVED — never `data`."""
    markers = scan_text(content.text)
    marker_ids = tuple(_marker_id(m) for m in markers)
    signal_ids = tuple(f"signal:{s}" for s in content.signals)

    if marker_ids:
        return RuleDecision(
            label=RuleLabel.INSTRUCTION,
            rule_version=policy.version,
            marker_ids=marker_ids,
            signal_ids=signal_ids,
        )
    if signal_ids and policy.structural_signals_escalate:
        return RuleDecision(
            label=RuleLabel.INSTRUCTION,
            rule_version=policy.version,
            marker_ids=(),
            signal_ids=signal_ids,
        )
    return RuleDecision(
        label=RuleLabel.UNRESOLVED,
        rule_version=policy.version,
        marker_ids=(),
        signal_ids=signal_ids,
    )
