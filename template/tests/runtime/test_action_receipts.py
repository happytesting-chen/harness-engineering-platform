"""Task 9 — action approval: REQUIRE_APPROVAL is a pause, never a bypass.

The two properties that make receipts safe to have at all:
1. A valid receipt converts REQUIRE_APPROVAL into CONTINUED policy evaluation — the
   inner gates still run, so an approved-but-hard-blocked action still dies at ②.
   "It never changes DENY to ALLOW" is a test, not a sentence.
2. Authority stays typed and single-use: exact action digest, expiring, nonce burned
   on success, and a content receipt in the approval slot is a TypeError.
"""
import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "Security-kit"))
sys.path.insert(0, str(_ROOT / "governance"))

import permission  # noqa: E402
import runtime_dispatcher  # noqa: E402
import runtime_screen  # noqa: E402
from runtime_dispatcher import RuntimeDispatcher  # noqa: E402

from runtime.contracts import Origin  # noqa: E402
from runtime.guarded import GuardedDispatcher  # noqa: E402
from runtime.review import (  # noqa: E402
    ActionReviewRequest,
    NonceStore,
    ReceiptVerifier,
    action_sha256,
    issue_action_receipt,
    issue_content_receipt,
    ContentReviewRequest,
)
from runtime.session import SessionPolicy, SessionState  # noqa: E402

MASTER_KEY = b"host-owned-master-key-32-bytes!!"
POLICY_SHA = "b" * 64


class Spy:
    def __init__(self):
        self.calls = 0

    def __call__(self, **kwargs):
        self.calls += 1
        return {"ok": True}


@contextmanager
def policy(tools=("send_email", "bash")):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "mcp-allowlist.json"
        path.write_text(json.dumps({
            "tools": [{"name": n, "description": n, "version": "1.0"} for n in tools],
            "egress_hosts": ["localhost"],
        }))
        originals = (permission.ALLOWLIST_PATH, runtime_dispatcher.record, runtime_screen._audit)
        permission.ALLOWLIST_PATH = path
        runtime_dispatcher.record = lambda *a: None
        runtime_screen._audit = lambda *a: None
        try:
            yield
        finally:
            permission.ALLOWLIST_PATH, runtime_dispatcher.record, runtime_screen._audit = originals


def _verifier():
    return ReceiptVerifier(
        master_key=MASTER_KEY, nonce_store=NonceStore(),
        policy_sha256=POLICY_SHA, rule_version="rules-v1",
        classifier_sha256="c" * 64,
    )


def _guarded(tools, verifier, **policy_kwargs):
    return GuardedDispatcher(
        inner=RuntimeDispatcher(tools),
        policy=SessionPolicy(require_approval=frozenset({"send_email", "bash"}), **policy_kwargs),
        state=SessionState(),
        verifier=verifier,
    )


def _receipt_for(tool, args, nonce="ar-1", ttl=300, now=1000):
    request = ActionReviewRequest(
        action_sha256=action_sha256(tool, args),
        policy_sha256=POLICY_SHA,
        reviewer_id="reviewer-1",
        ttl_seconds=ttl,
        nonce=nonce,
    )
    return issue_action_receipt(request, MASTER_KEY, now=now)


ARGS = {"to": "ops@localhost"}
ORIGINS = frozenset({Origin.USER_DIRECT})


def test_unapproved_sensitive_action_is_refused():
    spy = Spy()
    with policy():
        g = _guarded({"send_email": spy}, _verifier())
        try:
            g.execute("send_email", ARGS, origins=ORIGINS)
            raise AssertionError("REQUIRE_APPROVAL without a receipt must refuse")
        except PermissionError as exc:
            assert "approval" in str(exc)
    assert spy.calls == 0


def test_valid_receipt_lets_the_action_continue():
    spy = Spy()
    with policy():
        g = _guarded({"send_email": spy}, _verifier())
        g.execute("send_email", ARGS, origins=ORIGINS,
                  approval=_receipt_for("send_email", ARGS), now=1100)
    assert spy.calls == 1


def test_receipt_binds_the_exact_action():
    spy = Spy()
    with policy():
        g = _guarded({"send_email": spy}, _verifier())
        receipt = _receipt_for("send_email", {"to": "ops@localhost"})
        try:
            g.execute("send_email", {"to": "attacker@evil.example"},
                      origins=ORIGINS, approval=receipt, now=1100)
            raise AssertionError("a receipt for one action must not approve another")
        except PermissionError:
            pass
    assert spy.calls == 0


def test_receipt_is_single_use():
    spy = Spy()
    with policy():
        g = _guarded({"send_email": spy}, _verifier())
        receipt = _receipt_for("send_email", ARGS)
        g.execute("send_email", ARGS, origins=ORIGINS, approval=receipt, now=1100)
        try:
            g.execute("send_email", ARGS, origins=ORIGINS, approval=receipt, now=1100)
            raise AssertionError("a burned nonce must not approve again")
        except PermissionError:
            pass
    assert spy.calls == 1


def test_expired_receipt_is_refused():
    spy = Spy()
    with policy():
        g = _guarded({"send_email": spy}, _verifier())
        receipt = _receipt_for("send_email", ARGS, ttl=60, now=1000)
        try:
            g.execute("send_email", ARGS, origins=ORIGINS, approval=receipt, now=1061)
            raise AssertionError("an expired receipt must refuse")
        except PermissionError:
            pass
    assert spy.calls == 0


def test_action_receipt_does_not_override_deny():
    """The load-bearing one: approval means CONTINUED evaluation. A receipt for a
    hard-blocked command changes nothing — the inner gate still denies."""
    spy = Spy()
    with policy():
        g = _guarded({"bash": spy}, _verifier())
        blocked = {"command": "rm -rf /"}
        receipt = _receipt_for("bash", blocked)
        try:
            g.execute("bash", blocked, origins=ORIGINS, approval=receipt, now=1100)
            raise AssertionError("a receipt must never convert DENY to ALLOW")
        except PermissionError:
            pass
    assert spy.calls == 0


def test_content_receipt_in_the_approval_slot_is_a_type_error():
    spy = Spy()
    content_receipt = issue_content_receipt(ContentReviewRequest(
        content_sha256="a" * 64, origin=Origin.USER_DIRECT,
        policy_sha256=POLICY_SHA, rule_version="rules-v1",
        classifier_sha256="c" * 64, reviewer_id="r", ttl_seconds=300, nonce="n",
    ), MASTER_KEY, now=1000)
    with policy():
        g = _guarded({"send_email": spy}, _verifier())
        try:
            g.execute("send_email", ARGS, origins=ORIGINS,
                      approval=content_receipt, now=1100)
            raise AssertionError("a content receipt in the approval slot must be TypeError")
        except TypeError:
            pass
    assert spy.calls == 0


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
