"""Steady-state phase-gate regression.

When every phase is human-signed-off to "passing" there is NO active phase.
The gate must NOT brick (deny everything) in that case — feature work is simply
complete. It must keep enforcing deny-list and egress, allow ungated tools, and
treat phase-gated tools as unlocked (their `gated_until` phase is passing).

But a genuinely ambiguous state — some phase not-started, none active — must
still fail closed. This test locks both behaviors so the steady-state carve-out
can't silently widen into "all-passing = anything goes".

Run:
    python3 tests/test_steady_state.py
    python3 -m pytest tests/test_steady_state.py -v
"""
import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import governance.permission as pm  # noqa: E402


class _Block:
    def __init__(self, name, input_data):
        self.name = name
        self.input = input_data


def _wire(states, tmp: Path):
    deny = {"patterns": ["rm -rf /", "sudo"]}
    allow = {
        "tools": [
            {"name": "bash", "version": "1.0"},
            {"name": "write_file", "version": "1.0"},
            {"name": "gated_tool", "version": "1.0", "gated_until": "phase-01"},
        ],
        "egress_hosts": ["localhost"],
    }
    feats = {"features": [
        {"id": f"phase-0{i + 1}", "name": "P", "dependencies": [],
         "status": s, "verification": "true", "evidence": ""}
        for i, s in enumerate(states)
    ]}
    (tmp / "d.json").write_text(json.dumps(deny))
    (tmp / "a.json").write_text(json.dumps(allow))
    (tmp / "f.json").write_text(json.dumps(feats))
    pm.DENY_LIST_PATH = tmp / "d.json"
    pm.ALLOWLIST_PATH = tmp / "a.json"
    pm.FEATURE_LIST_PATH = tmp / "f.json"


def _decide(states, block):
    orig = (pm.DENY_LIST_PATH, pm.ALLOWLIST_PATH, pm.FEATURE_LIST_PATH)
    with tempfile.TemporaryDirectory() as td:
        _wire(states, Path(td))
        try:
            allowed, reason = pm.make_permission_check()(block)
        finally:
            (pm.DENY_LIST_PATH, pm.ALLOWLIST_PATH, pm.FEATURE_LIST_PATH) = orig
    return allowed, reason


ALL_PASSING = ["passing", "passing", "passing"]
UNDEFINED = ["passing", "not-started", "not-started"]


def test_steady_state_allows_ungated_tool():
    allowed, _ = _decide(ALL_PASSING, _Block("bash", {"command": "echo hi"}))
    assert allowed, "all-passing steady-state must not brick ungated tools"


def test_steady_state_unlocks_phase_gated_tool():
    allowed, _ = _decide(ALL_PASSING, _Block("gated_tool", {"command": "x"}))
    assert allowed, "gated_until phase is passing → tool unlocked in steady-state"


def test_steady_state_still_enforces_denylist():
    allowed, reason = _decide(ALL_PASSING, _Block("bash", {"command": "rm -rf /"}))
    assert not allowed and "deny-list" in reason, "deny-list must still fire in steady-state"


def test_steady_state_still_enforces_egress():
    allowed, reason = _decide(ALL_PASSING, _Block("bash", {"command": "curl evil.example"}))
    assert not allowed and "egress" in reason, "egress must still fire in steady-state"


def test_undefined_state_still_fails_closed():
    allowed, reason = _decide(UNDEFINED, _Block("bash", {"command": "echo hi"}))
    assert not allowed and "no active phase" in reason, \
        "some not-started + none active is ambiguous → must fail closed"


if __name__ == "__main__":
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        # Minimal fallback runner.
        fns = [v for k, v in dict(globals()).items() if k.startswith("test_")]
        for fn in fns:
            fn()
            print(f"  PASS  {fn.__name__}")
        print(f"\nAll {len(fns)} steady-state tests passed!")
