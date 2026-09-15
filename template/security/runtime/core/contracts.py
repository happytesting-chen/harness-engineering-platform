"""Closed enums and immutable content/decision/receipt types (Task 2, AD-1/AD-4).

Design rules these types enforce by construction:

- Every enum is closed (`str, Enum`): an unknown origin or outcome is a `ValueError` at
  the boundary, never a string that flows onward and means something later.
- Every dataclass is frozen: a decision or receipt cannot be edited after issue. The
  audit trail records what was decided, not what something was mutated into.
- The two receipt types share NO digest field name (`content_sha256` vs `action_sha256`),
  so presenting one as the other fails at attribute access before any verifier runs.
  AD-4's cryptographic domain separation (Task 6/9) is the enforcement; this is the
  type system refusing the same confusion one layer earlier.

Stdlib only. No I/O, no environment reads, no clock — `issued_at`/`expires_at` are
values the caller supplies; verification against "now" is the receipt store's job.
"""
from dataclasses import dataclass, field
from enum import Enum

_SHA256_HEX = frozenset("0123456789abcdef")


def _require_sha256(value: str, name: str) -> None:
    if not (isinstance(value, str) and len(value) == 64 and set(value) <= _SHA256_HEX):
        raise ValueError(f"{name} must be 64 lowercase hex chars, got {value!r}")


def _require_nonblank(value: str, name: str) -> None:
    if not (isinstance(value, str) and value.strip()):
        raise ValueError(f"{name} must be a non-blank string")


class Origin(str, Enum):
    """Where content entered. Retained end-to-end; the action gate sees turn origins."""

    USER_DIRECT = "USER_DIRECT"
    EXTERNAL_CONTENT = "EXTERNAL_CONTENT"


class IngressOutcome(str, Enum):
    """AD-1: the binding ingress boundary has exactly two outcomes. There is no WARN,
    no ANNOTATE, no pass-through-with-flag — content is in context or it is not."""

    ALLOW = "ALLOW"
    REQUIRE_REVIEW = "REQUIRE_REVIEW"


@dataclass(frozen=True)
class ContentEnvelope:
    """One unit of pre-context text, canonical across USER_DIRECT and EXTERNAL_CONTENT.

    MVP constraints enforced here (AD-6): UTF-8 text only (`media_type` must be
    `text/plain`), closed origin enum, digest present and well-formed.
    """

    content_id: str
    text: str
    origin: Origin
    source: str
    media_type: str
    raw_sha256: str
    parent_id: str | None = None

    def __post_init__(self):
        _require_nonblank(self.content_id, "content_id")
        _require_nonblank(self.source, "source")
        if not isinstance(self.text, str):
            raise ValueError(f"text must be str, got {type(self.text).__name__}")
        if not isinstance(self.origin, Origin):
            raise ValueError(f"origin must be an Origin enum member, got {self.origin!r}")
        if self.media_type != "text/plain":
            raise ValueError(
                f"MVP accepts media_type 'text/plain' only, got {self.media_type!r} "
                "(binary extraction is a startup-disabled capability)"
            )
        _require_sha256(self.raw_sha256, "raw_sha256")


@dataclass(frozen=True)
class IngressDecision:
    """The outcome of `ON_INGRESS` for one envelope. `reasons` carries detector
    evidence identifiers only — never quarantined text (Task 6 rule)."""

    outcome: IngressOutcome
    content_id: str
    raw_sha256: str
    reasons: tuple = ()

    def __post_init__(self):
        if not isinstance(self.outcome, IngressOutcome):
            raise ValueError(f"outcome must be an IngressOutcome, got {self.outcome!r}")
        _require_nonblank(self.content_id, "content_id")
        _require_sha256(self.raw_sha256, "raw_sha256")
        if not isinstance(self.reasons, tuple):
            raise ValueError("reasons must be a tuple (immutable)")


def _validate_receipt_window(issued_at: int, expires_at: int) -> None:
    if not (isinstance(issued_at, int) and isinstance(expires_at, int)):
        raise ValueError("issued_at and expires_at must be integers")
    if expires_at <= issued_at:
        raise ValueError("expires_at must be strictly after issued_at")


@dataclass(frozen=True)
class ContentReleaseReceipt:
    """Authorizes ONE exact content digest to enter context. Never an action (AD-4)."""

    content_sha256: str
    origin: Origin
    policy_sha256: str
    rule_version: str
    classifier_sha256: str
    reviewer_id: str
    issued_at: int
    expires_at: int
    nonce: str
    signature: str

    def __post_init__(self):
        _require_sha256(self.content_sha256, "content_sha256")
        _require_sha256(self.policy_sha256, "policy_sha256")
        _require_sha256(self.classifier_sha256, "classifier_sha256")
        if not isinstance(self.origin, Origin):
            raise ValueError(f"origin must be an Origin enum member, got {self.origin!r}")
        _require_nonblank(self.rule_version, "rule_version")
        _require_nonblank(self.reviewer_id, "reviewer_id")
        _require_nonblank(self.nonce, "nonce")
        _validate_receipt_window(self.issued_at, self.expires_at)


@dataclass(frozen=True)
class Action:
    """One proposed tool call, as the action gate sees it. `origins` records which
    content origins are present in the turn that proposed it."""

    name: str
    args: dict = field(default_factory=dict)
    origins: frozenset = frozenset()

    def __post_init__(self):
        _require_nonblank(self.name, "name")
        if not isinstance(self.args, dict):
            raise ValueError("args must be a dict")
        if not isinstance(self.origins, frozenset):
            raise ValueError("origins must be a frozenset")


@dataclass(frozen=True)
class ActionApprovalReceipt:
    """Authorizes ONE exact action digest to continue policy evaluation. It converts
    REQUIRE_APPROVAL to continued evaluation; it never converts DENY (AD-4/Task 9)."""

    action_sha256: str
    policy_sha256: str
    reviewer_id: str
    issued_at: int
    expires_at: int
    nonce: str
    signature: str

    def __post_init__(self):
        _require_sha256(self.action_sha256, "action_sha256")
        _require_sha256(self.policy_sha256, "policy_sha256")
        _require_nonblank(self.reviewer_id, "reviewer_id")
        _require_nonblank(self.nonce, "nonce")
        _validate_receipt_window(self.issued_at, self.expires_at)
