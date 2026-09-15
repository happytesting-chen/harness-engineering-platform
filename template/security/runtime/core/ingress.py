"""Binding ingress: strict rule + semantic aggregation, quarantine on withhold (Task 6, AD-1/AD-2).

The decision table, verbatim from the plan — four ways to withhold, one way in:

    rule INSTRUCTION  + (not consulted)        -> REQUIRE_REVIEW
    rule UNRESOLVED   + semantic DATA          -> ALLOW          <- the only allow
    rule UNRESOLVED   + semantic INSTRUCTION   -> REQUIRE_REVIEW
    rule UNRESOLVED   + semantic UNRESOLVED    -> REQUIRE_REVIEW
    rule UNRESOLVED   + semantic error/crash   -> REQUIRE_REVIEW
    content too large to read                  -> REQUIRE_REVIEW

Monotonic: nothing the classifier says can weaken a rule verdict — on a rule hit the
classifier is not even consulted. Every failure of the machinery lands on withhold.

Quarantine hygiene: the `IngressDecision` carries hashes and namespaced detector IDs
only. The raw text goes into the host-owned `QuarantineStore` under an opaque ID, and
is never copied into decision reasons, audit events, or receipts.
"""
import hashlib
import threading
from dataclasses import dataclass, field, replace

from .classifier import SemanticLabel
from .contracts import ContentEnvelope, IngressDecision, IngressOutcome
from .normalization import (
    ChunkPolicy,
    ContentTooLarge,
    NormalizationPolicy,
    chunk,
    normalize,
)
from .rules import RuleLabel, RulePolicy, evaluate_rules


@dataclass(frozen=True)
class IngressPolicy:
    normalization: NormalizationPolicy = field(default_factory=NormalizationPolicy)
    chunking: ChunkPolicy = field(default_factory=ChunkPolicy)
    rules: RulePolicy = field(default_factory=lambda: RulePolicy(version="rules-v1"))


@dataclass(frozen=True)
class QuarantineRecord:
    quarantine_id: str
    content_id: str
    raw_sha256: str
    origin: str
    source: str
    reasons: tuple
    text: str  # lives HERE and nowhere else


class QuarantineStore:
    """Host-owned holding area for withheld content. Opaque, deterministic IDs
    (digest-derived, so replaying the same content re-uses the same record)."""

    def __init__(self):
        self._records = {}
        self._lock = threading.Lock()

    def put(self, envelope: ContentEnvelope, reasons: tuple) -> str:
        qid = "q-" + hashlib.sha256(
            (envelope.raw_sha256 + envelope.origin.value).encode()
        ).hexdigest()[:16]
        with self._lock:
            self._records[qid] = QuarantineRecord(
                quarantine_id=qid,
                content_id=envelope.content_id,
                raw_sha256=envelope.raw_sha256,
                origin=envelope.origin.value,
                source=envelope.source,
                reasons=reasons,
                text=envelope.text,
            )
        return qid

    def get(self, quarantine_id: str) -> QuarantineRecord:
        with self._lock:
            return self._records[quarantine_id]

    def count(self) -> int:
        with self._lock:
            return len(self._records)


# IngressDecision gains an optional quarantine reference without widening the
# contracts module: compose here.
@dataclass(frozen=True)
class QuarantinedIngressDecision(IngressDecision):
    quarantine_id: str | None = None


def _withhold(envelope: ContentEnvelope, reasons: tuple, quarantine) -> QuarantinedIngressDecision:
    qid = quarantine.put(envelope, reasons) if quarantine is not None else None
    return QuarantinedIngressDecision(
        outcome=IngressOutcome.REQUIRE_REVIEW,
        content_id=envelope.content_id,
        raw_sha256=envelope.raw_sha256,
        reasons=reasons,
        quarantine_id=qid,
    )


def evaluate_ingress(envelope: ContentEnvelope, *, policy: IngressPolicy,
                     classifier, quarantine: QuarantineStore | None = None,
                     receipts=None, now: int = 0) -> QuarantinedIngressDecision:
    """One envelope through the strict pipeline. `receipts`, when provided, is an
    object with `redeem(envelope, now) -> bool` — a valid, unused ContentReleaseReceipt
    for this exact digest bypasses re-classification (and only that)."""
    if receipts is not None and receipts.redeem(envelope, now):
        return QuarantinedIngressDecision(
            outcome=IngressOutcome.ALLOW,
            content_id=envelope.content_id,
            raw_sha256=envelope.raw_sha256,
            reasons=("receipt:content-release",),
            quarantine_id=None,
        )

    try:
        normalized = normalize(envelope, policy.normalization)
        chunks = chunk(normalized, policy.chunking)
    except ContentTooLarge:
        return _withhold(envelope, ("size:too-large",), quarantine)

    # rule layer over every chunk — a hit anywhere settles it, classifier not consulted
    rule_reasons = []
    for piece in chunks:
        piece_content = replace(normalized, text=piece.text)
        decision = evaluate_rules(piece_content, policy.rules)
        if decision.label is RuleLabel.INSTRUCTION:
            rule_reasons.extend(decision.marker_ids or decision.signal_ids)
    if rule_reasons:
        return _withhold(envelope, ("rule:instruction", *dict.fromkeys(rule_reasons)), quarantine)

    # semantic layer — strictest chunk wins; any machinery failure is a withhold
    for piece in chunks:
        try:
            semantic = classifier.classify(piece)
        except Exception as exc:  # a classifier that raises is a broken classifier
            return _withhold(
                envelope, ("semantic:error:" + type(exc).__name__,), quarantine
            )
        if semantic.label is SemanticLabel.INSTRUCTION:
            return _withhold(envelope, ("semantic:instruction",), quarantine)
        if semantic.label is SemanticLabel.UNRESOLVED:
            reason = "semantic:unresolved" + (f":{semantic.reason}" if semantic.reason else "")
            return _withhold(envelope, (reason,), quarantine)

    return QuarantinedIngressDecision(
        outcome=IngressOutcome.ALLOW,
        content_id=envelope.content_id,
        raw_sha256=envelope.raw_sha256,
        reasons=("rule:unresolved", "semantic:data"),
        quarantine_id=None,
    )
