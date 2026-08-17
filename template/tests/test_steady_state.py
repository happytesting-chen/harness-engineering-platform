"""Phase-gate regression: steady state, and who is allowed to unlock a gated tool.

Two properties, and the second one used to be asserted backwards by this file.

1.  AVAILABILITY. When every phase is "passing" there is no active phase. The gate
    must not brick — feature work is simply complete. Ungated tools keep working,
    and deny-list and egress keep firing.

2.  NO SELF-PROMOTION. A `gated_until` tool is unlocked by `signed_off_phases` in
    governance/mcp-allowlist.json — a protected path, so human-only. It is NOT
    unlocked by `status` in Harness-Best-Practice/feature_list.json, which is the
    agent's own worklog and stays editable during development by design.

The original version of this file asserted the opposite of (2): a test named
`test_steady_state_unlocks_phase_gated_tool` required that all-phases-passing
unlock the gated tool. That is exactly the escalation — the agent writes its own
worklog, so it could satisfy the condition itself. The test passed, `init.sh` was
green, and the hole was pinned in place by a green test. Measured on the tree of
2026-08-17, three separate edits to feature_list.json reached ALLOW; all three are
now denied, and `test_agent_cannot_self_promote_by_editing_the_worklog` drives all
three rather than trusting the fix.

Keeping (1) and (2) in one file is deliberate: they pull against each other. The
availability tests are what stops a future fix for (2) from being "deny everything
at steady state", and (2) is what stops (1) from widening into "all passing =
anything goes".

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


def _wire(states, tmp: Path, signed_off=None, drop=()):
    """Provision a throwaway policy set.

    `signed_off` is the allowlist's `signed_off_phases`. Default None means the key
    is ABSENT, which is the shipped-template state and must behave as `[]`.
    `drop` removes phase ids from the feature list, to drive the missing-prerequisite
    vector — the old gate matched on id and allowed when it found none.
    """
    deny = {"patterns": ["rm -rf /", "sudo"]}
    allow = {
        "tools": [
            {"name": "bash", "version": "1.0"},
            {"name": "write_file", "version": "1.0"},
            {"name": "gated_tool", "version": "1.0", "gated_until": "phase-01"},
        ],
        "egress_hosts": ["localhost"],
    }
    if signed_off is not None:
        allow["signed_off_phases"] = signed_off
    feats = {"features": [
        {"id": f"phase-0{i + 1}", "name": "P", "dependencies": [],
         "status": s, "verification": "true", "evidence": ""}
        for i, s in enumerate(states)
        if f"phase-0{i + 1}" not in drop
    ]}
    (tmp / "d.json").write_text(json.dumps(deny))
    (tmp / "a.json").write_text(json.dumps(allow))
    (tmp / "f.json").write_text(json.dumps(feats))
    pm.DENY_LIST_PATH = tmp / "d.json"
    pm.ALLOWLIST_PATH = tmp / "a.json"
    pm.FEATURE_LIST_PATH = tmp / "f.json"


def _decide(states, block, signed_off=None, drop=()):
    orig = (pm.DENY_LIST_PATH, pm.ALLOWLIST_PATH, pm.FEATURE_LIST_PATH)
    with tempfile.TemporaryDirectory() as td:
        _wire(states, Path(td), signed_off=signed_off, drop=drop)
        try:
            allowed, reason = pm.make_permission_check()(block)
        finally:
            (pm.DENY_LIST_PATH, pm.ALLOWLIST_PATH, pm.FEATURE_LIST_PATH) = orig
    return allowed, reason


ALL_PASSING = ["passing", "passing", "passing"]
UNDEFINED = ["passing", "not-started", "not-started"]
SHIPPED = ["active", "not-started", "not-started"]
GATED = _Block("gated_tool", {"command": "x"})


def test_steady_state_allows_ungated_tool():
    allowed, _ = _decide(ALL_PASSING, _Block("bash", {"command": "echo hi"}))
    assert allowed, "all-passing steady-state must not brick ungated tools"


def test_steady_state_does_not_unlock_phase_gated_tool():
    """The inversion. This is the assertion that used to read the other way.

    All phases "passing" and no `signed_off_phases` must still DENY: the worklog
    saying a phase passed is not a human saying it is signed off.
    """
    allowed, reason = _decide(ALL_PASSING, GATED)
    assert not allowed, (
        "all-phases-passing unlocked a gated tool. That is self-promotion: the agent "
        "writes feature_list.json, so it can produce this state itself."
    )
    assert "signed off" in reason, reason


def test_a_signed_off_phase_unlocks_the_gated_tool():
    """The human path has to work, or the gate is just a brick wall."""
    allowed, _ = _decide(SHIPPED, GATED, signed_off=["phase-01"])
    assert allowed, "phase-01 in signed_off_phases must unlock a tool gated on it"


def test_agent_cannot_self_promote_by_editing_the_worklog():
    """Drives all three edits that reached ALLOW before the split, measured 2026-08-17.

    Each is a plausible thing an agent does to its own worklog, and each used to buy
    it a tool a human had not released.
    """
    doors = [
        ("mark the prerequisite passing and move on",
         ["passing", "active", "not-started"], ()),
        ("mark every phase passing (reaches the steady-state carve-out)",
         ALL_PASSING, ()),
        ("delete the prerequisite entry entirely (id match finds nothing)",
         ["passing", "active", "not-started"], ("phase-01",)),
    ]
    for label, states, drop in doors:
        allowed, reason = _decide(states, GATED, drop=drop)
        assert not allowed, f"self-promotion door open: {label}"
        assert "signed off" in reason, f"{label}: unexpected reason {reason!r}"


def test_absent_signed_off_key_denies_rather_than_allowing():
    """The shipped template omits the key. Absent must mean none, not all."""
    allowed, reason = _decide(SHIPPED, GATED, signed_off=None)
    assert not allowed and "signed off" in reason, reason


def test_signed_off_phases_as_a_bare_string_does_not_substring_match():
    """`"phase-0" in "phase-01"` is True. A human typo must not unlock anything.

    Guards the isinstance check in check_phase_gate: without it a string value turns
    the membership test into a substring test, and every phase whose id is a prefix
    of the typed value silently unlocks.
    """
    for bad in ("phase-01", "phase-01,phase-02", "all"):
        allowed, reason = _decide(SHIPPED, GATED, signed_off=bad)
        assert not allowed, f"signed_off_phases={bad!r} unlocked a gated tool"
        assert "signed off" in reason, reason


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
