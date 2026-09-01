"""Task 8 — the composed action plane: session ceilings, origin rules, schema binding.

AD-7 compliance is structural: `GuardedDispatcher` WRAPS the existing
`RuntimeDispatcher` — it holds no policy predicate of the inner gates and no pattern.
What it adds is exactly what the per-call gate cannot see: the SEQUENCE (ceilings with
reserve/commit/rollback, correct under concurrency) and the TURN (origin-sensitive
rules over where this turn's content came from).

Every denial is proven by `calls == 0` — the tool never ran — and the composition test
proves the inner gate still fires through the wrapper: a deny-listed command dies at
gate ② even when the session layer would have allowed it.
"""
import asyncio
import json
import sys
import tempfile
import threading
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
from runtime.session import SessionPolicy, SessionState  # noqa: E402


class Spy:
    def __init__(self):
        self.calls = 0

    def __call__(self, **kwargs):
        self.calls += 1
        return {"ok": True}


@contextmanager
def policy(tools=("fetch", "send_email", "bash")):
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


def _guarded(tools, session_policy):
    return GuardedDispatcher(
        inner=RuntimeDispatcher(tools),
        policy=session_policy,
        state=SessionState(),
    )


def test_schema_violation_denies_before_the_tool_runs():
    spy = Spy()
    with policy():
        g = _guarded({"fetch": spy}, SessionPolicy(
            arg_schemas={"fetch": {"url": str}},
        ))
        try:
            g.execute("fetch", {"url": 123}, origins=frozenset({Origin.USER_DIRECT}))
            raise AssertionError("wrong arg type must deny")
        except PermissionError:
            pass
        try:
            g.execute("fetch", {"url": "http://localhost/x", "shell": "rm -rf /"},
                      origins=frozenset({Origin.USER_DIRECT}))
            raise AssertionError("unknown arg must deny")
        except PermissionError:
            pass
    assert spy.calls == 0


def test_origin_rule_denies_tainted_turn():
    spy = Spy()
    with policy():
        g = _guarded({"send_email": spy}, SessionPolicy(
            origin_rules={"send_email": frozenset({Origin.USER_DIRECT})},
        ))
        try:
            g.execute("send_email", {"to": "x@localhost"},
                      origins=frozenset({Origin.USER_DIRECT, Origin.EXTERNAL_CONTENT}))
            raise AssertionError("a turn tainted by external content must not send email")
        except PermissionError:
            pass
        assert spy.calls == 0
        g.execute("send_email", {"to": "x@localhost"},
                  origins=frozenset({Origin.USER_DIRECT}))
        assert spy.calls == 1


def test_per_tool_ceiling_holds():
    spy = Spy()
    with policy():
        g = _guarded({"fetch": spy}, SessionPolicy(max_calls={"fetch": 2}))
        for _ in range(2):
            g.execute("fetch", {"url": "http://localhost/x"},
                      origins=frozenset({Origin.USER_DIRECT}))
        try:
            g.execute("fetch", {"url": "http://localhost/x"},
                      origins=frozenset({Origin.USER_DIRECT}))
            raise AssertionError("the third call must exceed the ceiling")
        except PermissionError as exc:
            assert "ceiling" in str(exc)
    assert spy.calls == 2


def test_total_ceiling_spans_tools():
    a, b = Spy(), Spy()
    with policy():
        g = _guarded({"fetch": a, "bash": b}, SessionPolicy(total_max_calls=2))
        g.execute("fetch", {"url": "http://localhost/x"}, origins=frozenset({Origin.USER_DIRECT}))
        g.execute("bash", {"command": "ls"}, origins=frozenset({Origin.USER_DIRECT}))
        try:
            g.execute("fetch", {"url": "http://localhost/x"}, origins=frozenset({Origin.USER_DIRECT}))
            raise AssertionError("total ceiling must hold across tools")
        except PermissionError:
            pass
    assert a.calls + b.calls == 2


def test_failed_tool_rolls_back_its_reservation():
    def broken(**kwargs):
        raise RuntimeError("tool crashed")

    spy = Spy()
    with policy():
        g = _guarded({"fetch": spy, "bash": broken}, SessionPolicy(total_max_calls=1))
        try:
            g.execute("bash", {"command": "ls"}, origins=frozenset({Origin.USER_DIRECT}))
        except RuntimeError:
            pass
        # the crashed call must not consume the budget
        g.execute("fetch", {"url": "http://localhost/x"}, origins=frozenset({Origin.USER_DIRECT}))
        assert spy.calls == 1


def test_concurrent_reservations_admit_exactly_one():
    spy = Spy()
    with policy():
        g = _guarded({"fetch": spy}, SessionPolicy(max_calls={"fetch": 1}))
        barrier = threading.Barrier(2)
        outcomes = []

        def attempt():
            barrier.wait()
            try:
                g.execute("fetch", {"url": "http://localhost/x"},
                          origins=frozenset({Origin.USER_DIRECT}))
                outcomes.append("ran")
            except PermissionError:
                outcomes.append("denied")

        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    assert sorted(outcomes) == ["denied", "ran"]
    assert spy.calls == 1


def test_async_wrapper_enforces_the_same_ceiling():
    spy = Spy()

    async def race():
        with policy():
            g = _guarded({"fetch": spy}, SessionPolicy(max_calls={"fetch": 1}))
            results = await asyncio.gather(
                g.aexecute("fetch", {"url": "http://localhost/x"},
                           origins=frozenset({Origin.USER_DIRECT})),
                g.aexecute("fetch", {"url": "http://localhost/x"},
                           origins=frozenset({Origin.USER_DIRECT})),
                return_exceptions=True,
            )
            return results

    results = asyncio.run(race())
    denied = [r for r in results if isinstance(r, PermissionError)]
    assert len(denied) == 1
    assert spy.calls == 1


def test_inner_gate_still_fires_through_the_wrapper():
    """The composition proof: gate ② (deny-list, egress, allowlist membership) is the
    inner dispatcher's, and wrapping must not bypass it. A deny-listed command dies at
    ② even though the session layer has budget for it."""
    spy = Spy()
    with policy():
        g = _guarded({"bash": spy}, SessionPolicy())
        try:
            g.execute("bash", {"command": "rm -rf /"}, origins=frozenset({Origin.USER_DIRECT}))
            raise AssertionError("the inner deny-list must still fire through the wrapper")
        except PermissionError:
            pass
        assert spy.calls == 0
        # and the rollback happened: budget intact for a legitimate call
        g.execute("bash", {"command": "ls"}, origins=frozenset({Origin.USER_DIRECT}))
        assert spy.calls == 1


def test_wrapper_owns_no_gate_predicate():
    """AD-7 anti-drift: the wrapper adds sequence/turn rules only. No deny-list logic,
    no egress logic, no allowlist membership check duplicated from the inner gate."""
    for name in ("guarded.py", "session.py"):
        source = (_ROOT / "Security-kit" / "runtime" / name).read_text(encoding="utf-8")
        assert "re.compile" not in source
        for token in ("deny-list", "deny_list", "egress_hosts", "check_egress",
                      "check_deny_list", "check_phase_gate", "check_protected_paths"):
            assert token not in source, f"{name} must not re-implement {token}"


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
