"""Task 2 — closed, immutable content/decision/receipt types.

The receipts test is the load-bearing one: content-release and action-approval are
DIFFERENT types with different fields, so the type system itself refuses the confusion
the receipt verifier must also refuse (AD-4). Runs standalone or under pytest.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "Security-kit"))

from runtime.contracts import (  # noqa: E402
    Action,
    ActionApprovalReceipt,
    ContentEnvelope,
    ContentReleaseReceipt,
    IngressDecision,
    IngressOutcome,
    Origin,
)

SHA_A = "a" * 64
SHA_B = "b" * 64


def _envelope(**overrides):
    kwargs = dict(
        content_id="env-1",
        text="ordinary shipping information",
        origin=Origin.EXTERNAL_CONTENT,
        source="retrieve_report",
        media_type="text/plain",
        raw_sha256=SHA_A,
    )
    kwargs.update(overrides)
    return ContentEnvelope(**kwargs)


def _content_receipt(**overrides):
    kwargs = dict(
        content_sha256=SHA_A,
        origin=Origin.USER_DIRECT,
        policy_sha256=SHA_B,
        rule_version="rules-v1",
        classifier_sha256=SHA_B,
        reviewer_id="reviewer-1",
        issued_at=1,
        expires_at=2,
        nonce="content-nonce",
        signature="sig",
    )
    kwargs.update(overrides)
    return ContentReleaseReceipt(**kwargs)


def test_content_and_action_receipts_are_not_interchangeable():
    content = _content_receipt()
    assert content.content_sha256 == SHA_A
    assert not hasattr(content, "action_sha256"), (
        "a content receipt must not carry an action digest"
    )
    action = ActionApprovalReceipt(
        action_sha256=SHA_A,
        policy_sha256=SHA_B,
        reviewer_id="reviewer-1",
        issued_at=1,
        expires_at=2,
        nonce="action-nonce",
        signature="sig",
    )
    assert not hasattr(action, "content_sha256"), (
        "an action receipt must not carry a content digest"
    )


def test_envelope_is_immutable():
    env = _envelope()
    try:
        env.text = "mutated"
        raise AssertionError("ContentEnvelope must be frozen")
    except AttributeError:
        pass
    except Exception as exc:  # dataclasses raise FrozenInstanceError (a TypeError subclass? no — AttributeError subclass)
        assert type(exc).__name__ == "FrozenInstanceError"


def test_envelope_rejects_blank_id():
    try:
        _envelope(content_id="   ")
        raise AssertionError("blank content_id must be rejected")
    except ValueError:
        pass


def test_envelope_rejects_non_text_plain_media():
    try:
        _envelope(media_type="application/pdf")
        raise AssertionError("non-text/plain media must be rejected in the MVP")
    except ValueError:
        pass


def test_envelope_rejects_invalid_sha256():
    for bad in ("", "xyz", "A" * 64, "a" * 63):
        try:
            _envelope(raw_sha256=bad)
            raise AssertionError(f"invalid sha256 {bad!r} must be rejected")
        except ValueError:
            pass


def test_envelope_rejects_non_enum_origin():
    try:
        _envelope(origin="USER_DIRECT")  # a str is not an Origin
        raise AssertionError("string origin must be rejected — closed enum only")
    except ValueError:
        pass


def test_ingress_outcome_is_a_closed_two_value_enum():
    assert {o.value for o in IngressOutcome} == {"ALLOW", "REQUIRE_REVIEW"}


def test_ingress_decision_requires_outcome_enum():
    d = IngressDecision(
        outcome=IngressOutcome.REQUIRE_REVIEW,
        content_id="env-1",
        raw_sha256=SHA_A,
        reasons=("rule:instruction",),
    )
    assert d.outcome is IngressOutcome.REQUIRE_REVIEW
    try:
        IngressDecision(
            outcome="ALLOW", content_id="env-1", raw_sha256=SHA_A, reasons=()
        )
        raise AssertionError("string outcome must be rejected")
    except ValueError:
        pass


def test_action_is_immutable_with_frozen_args():
    a = Action(name="send_email", args={"to": "x@example.com"}, origins=frozenset({Origin.USER_DIRECT}))
    assert a.args == {"to": "x@example.com"}
    try:
        a.name = "other"
        raise AssertionError("Action must be frozen")
    except AttributeError:
        pass
    except Exception as exc:
        assert type(exc).__name__ == "FrozenInstanceError"


def test_receipt_expiry_must_follow_issue():
    try:
        _content_receipt(issued_at=5, expires_at=5)
        raise AssertionError("expires_at must be strictly after issued_at")
    except ValueError:
        pass


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
