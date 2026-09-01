"""Content-release receipts: HMAC-signed, exact-digest, expiring, single-use (Task 6, AD-4).

Authority separation, enforced three ways at once:

- **Type level** — `verify_content` refuses anything but a `ContentReleaseReceipt` with
  `TypeError`; `verify_action` refuses anything but an `ActionApprovalReceipt`. The
  confusion fails before any cryptography runs.
- **Key level** — signing keys are derived from the host's master key with fixed domain
  labels (`runtime-security/content-receipt/v1` here; the action domain in Task 9), so a
  signature from one domain can never verify in the other even on identical bytes.
- **Context level** — the receipt binds the policy digest, rule version and classifier
  digest that were in force at review time. If any of those drift, the receipt is void:
  releasing content judged under different rules is a different decision.

The master key is passed in as bytes by the host and is never read from agent-visible
configuration. Nonces are consumed atomically; a replayed receipt fails on its second
presentation. Verification uses `hmac.compare_digest` throughout. Stdlib only.
"""
import hashlib
import hmac
import json
import threading
from dataclasses import dataclass

from .contracts import Action, ActionApprovalReceipt, ContentEnvelope, ContentReleaseReceipt

CONTENT_DOMAIN = b"runtime-security/content-receipt/v1"
ACTION_DOMAIN = b"runtime-security/action-approval/v1"


def _derive_key(master_key: bytes, domain: bytes) -> bytes:
    if not isinstance(master_key, bytes) or len(master_key) < 16:
        raise ValueError("master key must be bytes, at least 16 bytes long")
    return hmac.new(master_key, domain, hashlib.sha256).digest()


def _sign_payload(key: bytes, payload: bytes) -> str:
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def _content_payload(fields: dict) -> bytes:
    """Canonical bytes: sorted compact JSON of every field except the signature."""
    return json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")


class NonceStore:
    """Single-use nonce consumption, atomic under a lock. In-memory for the MVP;
    the host owns persistence if it needs receipts to survive a restart."""

    def __init__(self):
        self._used = set()
        self._lock = threading.Lock()

    def consume(self, nonce: str) -> bool:
        with self._lock:
            if nonce in self._used:
                return False
            self._used.add(nonce)
            return True


@dataclass(frozen=True)
class ContentReviewRequest:
    """What a reviewer approves: one exact digest, in one exact detection context."""

    content_sha256: str
    origin: object
    policy_sha256: str
    rule_version: str
    classifier_sha256: str
    reviewer_id: str
    ttl_seconds: int
    nonce: str
    quarantine_id: str = ""

    def __post_init__(self):
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")


def _receipt_fields(receipt: ContentReleaseReceipt) -> dict:
    return {
        "kind": "content-release",
        "content_sha256": receipt.content_sha256,
        "origin": receipt.origin.value,
        "policy_sha256": receipt.policy_sha256,
        "rule_version": receipt.rule_version,
        "classifier_sha256": receipt.classifier_sha256,
        "reviewer_id": receipt.reviewer_id,
        "issued_at": receipt.issued_at,
        "expires_at": receipt.expires_at,
        "nonce": receipt.nonce,
    }


def issue_content_receipt(request: ContentReviewRequest, master_key: bytes, now: int) -> ContentReleaseReceipt:
    """Sign one exact content digest for release. The receipt carries digests and
    identities only — never a copy of the content."""
    key = _derive_key(master_key, CONTENT_DOMAIN)
    unsigned = ContentReleaseReceipt(
        content_sha256=request.content_sha256,
        origin=request.origin,
        policy_sha256=request.policy_sha256,
        rule_version=request.rule_version,
        classifier_sha256=request.classifier_sha256,
        reviewer_id=request.reviewer_id,
        issued_at=now,
        expires_at=now + request.ttl_seconds,
        nonce=request.nonce,
        signature="",
    )
    signature = _sign_payload(key, _content_payload(_receipt_fields(unsigned)))
    import dataclasses
    return dataclasses.replace(unsigned, signature=signature)


class ReceiptVerifier:
    """Holds the verification context: the master key, the nonce store, and the
    policy/rule/classifier digests currently in force."""

    def __init__(self, *, master_key: bytes, nonce_store: NonceStore,
                 policy_sha256: str, rule_version: str, classifier_sha256: str):
        self._content_key = _derive_key(master_key, CONTENT_DOMAIN)
        self._action_key = _derive_key(master_key, ACTION_DOMAIN)
        self._nonces = nonce_store
        self._policy_sha256 = policy_sha256
        self._rule_version = rule_version
        self._classifier_sha256 = classifier_sha256

    def verify_content(self, receipt, envelope: ContentEnvelope, *, now: int) -> bool:
        if not isinstance(receipt, ContentReleaseReceipt):
            raise TypeError(
                f"content release requires a ContentReleaseReceipt, got "
                f"{type(receipt).__name__} — an action approval can never mark content safe"
            )
        expected = _sign_payload(self._content_key, _content_payload(_receipt_fields(receipt)))
        if not hmac.compare_digest(expected, receipt.signature):
            return False
        if not (receipt.issued_at <= now <= receipt.expires_at):
            return False
        if not hmac.compare_digest(receipt.content_sha256, envelope.raw_sha256):
            return False
        if receipt.origin is not envelope.origin:
            return False
        # context binding: the rules in force must be the rules the reviewer saw
        if not (hmac.compare_digest(receipt.policy_sha256, self._policy_sha256)
                and receipt.rule_version == self._rule_version
                and hmac.compare_digest(receipt.classifier_sha256, self._classifier_sha256)):
            return False
        # last: consume the nonce only after everything else holds
        return self._nonces.consume(receipt.nonce)

    def verify_action(self, receipt, action: Action, *, now: int) -> bool:
        if not isinstance(receipt, ActionApprovalReceipt):
            raise TypeError(
                f"action approval requires an ActionApprovalReceipt, got "
                f"{type(receipt).__name__} — a content release can never authorize an action"
            )
        raise NotImplementedError(
            "action receipt verification lands in Task 9; the type gate above is "
            "deliberately in place first"
        )
