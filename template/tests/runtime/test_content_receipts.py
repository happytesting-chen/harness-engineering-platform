"""Task 6 — content-release receipts: exact-digest, expiring, single-use, type-separated.

The authority-separation tests are the point: a content receipt presented as an action
approval must fail at the TYPE level (AD-4), and a receipt signed under the action
domain key must not verify under the content domain even with identical fields —
domain separation is cryptographic, not conventional.
"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "Security-kit"))

from runtime.contracts import (  # noqa: E402
    Action,
    ActionApprovalReceipt,
    ContentEnvelope,
    Origin,
)
from runtime.review import (  # noqa: E402
    CONTENT_DOMAIN,
    ContentReviewRequest,
    NonceStore,
    ReceiptVerifier,
    _derive_key,
    _sign_payload,
    issue_content_receipt,
)

MASTER_KEY = b"host-owned-master-key-32-bytes!!"
TEXT = "finance report body, previously quarantined"
DIGEST = hashlib.sha256(TEXT.encode()).hexdigest()


def _envelope(text=TEXT):
    return ContentEnvelope(
        content_id="env-9",
        text=text,
        origin=Origin.EXTERNAL_CONTENT,
        source="retrieve_report",
        media_type="text/plain",
        raw_sha256=hashlib.sha256(text.encode()).hexdigest(),
    )


def _request(**overrides):
    kwargs = dict(
        content_sha256=DIGEST,
        origin=Origin.EXTERNAL_CONTENT,
        policy_sha256="b" * 64,
        rule_version="rules-v1",
        classifier_sha256="c" * 64,
        reviewer_id="reviewer-1",
        ttl_seconds=300,
        nonce="nonce-001",
    )
    kwargs.update(overrides)
    return ContentReviewRequest(**kwargs)


def _verifier():
    return ReceiptVerifier(
        master_key=MASTER_KEY,
        nonce_store=NonceStore(),
        policy_sha256="b" * 64,
        rule_version="rules-v1",
        classifier_sha256="c" * 64,
    )


def test_valid_receipt_verifies_once_and_only_once():
    receipt = issue_content_receipt(_request(), MASTER_KEY, now=1000)
    v = _verifier()
    assert v.verify_content(receipt, _envelope(), now=1100)
    assert not v.verify_content(receipt, _envelope(), now=1100), "nonce must be single-use"


def test_expired_receipt_is_refused():
    receipt = issue_content_receipt(_request(ttl_seconds=60), MASTER_KEY, now=1000)
    assert not _verifier().verify_content(receipt, _envelope(), now=1061)


def test_digest_mismatch_is_refused():
    receipt = issue_content_receipt(_request(), MASTER_KEY, now=1000)
    other = _envelope("completely different content")
    assert not _verifier().verify_content(receipt, other, now=1100)


def test_tampered_signature_is_refused():
    receipt = issue_content_receipt(_request(), MASTER_KEY, now=1000)
    forged = ContentEnvelope  # noqa: F841  (readability)
    import dataclasses
    tampered = dataclasses.replace(receipt, reviewer_id="attacker")
    assert not _verifier().verify_content(tampered, _envelope(), now=1100)


def test_wrong_master_key_is_refused():
    receipt = issue_content_receipt(_request(), b"some-other-key-entirely-000000!!", now=1000)
    assert not _verifier().verify_content(receipt, _envelope(), now=1100)


def test_content_receipt_cannot_authorize_action():
    receipt = issue_content_receipt(_request(), MASTER_KEY, now=1000)
    action = Action(name="send_email", args={}, origins=frozenset())
    try:
        _verifier().verify_action(receipt, action, now=1100)
        raise AssertionError("a content receipt must be a TypeError as an action approval")
    except TypeError:
        pass


def test_action_receipt_cannot_release_content():
    action_receipt = ActionApprovalReceipt(
        action_sha256="a" * 64, policy_sha256="b" * 64, reviewer_id="r",
        issued_at=1, expires_at=100, nonce="n", signature="s",
    )
    try:
        _verifier().verify_content(action_receipt, _envelope(), now=50)
        raise AssertionError("an action receipt must be a TypeError as a content release")
    except TypeError:
        pass


def test_domain_keys_differ():
    content_key = _derive_key(MASTER_KEY, CONTENT_DOMAIN)
    action_key = _derive_key(MASTER_KEY, b"runtime-security/action-approval/v1")
    assert content_key != action_key
    # a payload signed under the action domain must not verify under content
    payload = b"identical payload bytes"
    assert _sign_payload(content_key, payload) != _sign_payload(action_key, payload)


def test_receipt_context_binding():
    """A receipt issued under one policy/classifier context must not verify in another
    — releasing content that was judged under different rules is a different decision."""
    receipt = issue_content_receipt(_request(), MASTER_KEY, now=1000)
    drifted = ReceiptVerifier(
        master_key=MASTER_KEY, nonce_store=NonceStore(),
        policy_sha256="d" * 64,  # policy changed since review
        rule_version="rules-v1", classifier_sha256="c" * 64,
    )
    assert not drifted.verify_content(receipt, _envelope(), now=1100)


if __name__ == "__main__":
    try:
        import pytest
        raise SystemExit(pytest.main([__file__, "-q"]))
    except ImportError:
        failures = 0
        tests = [(n, f) for n, f in sorted(globals().items())
                 if n.startswith("test_") and callable(f)]
        for name, fn in tests:
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {name}: {exc}")
        print(f"Results: {len(tests) - failures} passed, {failures} failed")
        raise SystemExit(1 if failures else 0)
