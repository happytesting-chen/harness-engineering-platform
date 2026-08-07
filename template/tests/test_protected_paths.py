"""
Ground-truth tests for Gate 1b — protected write targets (control S2.4).

Why this file exists: `check_deny_list` inspects the shell *command* string, but a
Write/Edit/MultiEdit/NotebookEdit payload carries `file_path` and no `command`. So
before Gate 1b, a file-editing tool call targeting `permission.py` or
`deny-list.json` was invisible to every gate — the agent could edit the very
mechanism constraining it, while SECURITY.md S2.4 claimed "mechanism is immutable".

These tests pin the four properties that make the fix worth having:
  1. It blocks the direct write.
  2. It cannot be evaded by path traversal / absolute paths / redundant separators.
  3. It cannot be disabled by editing policy (built-ins are enforced unconditionally).
  4. It does not block ordinary project writes (no false positives).

Runnable with:
    python3 -m pytest tests/test_protected_paths.py -v
    python3 tests/test_protected_paths.py
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import governance.permission as permission  # noqa: E402

PROJECT_ROOT = Path(__file__).parent.parent


class Block:
    """Minimal Block-like object matching what make_permission_check consumes."""

    def __init__(self, name: str, input_data: dict):
        self.name = name
        self.input = input_data


def _check(tool: str, tool_input: dict):
    return permission.make_permission_check()(Block(tool, tool_input))


# ---------------------------------------------------------------------------
# 1. The direct write is blocked
# ---------------------------------------------------------------------------

MECHANISM_AND_POLICY = [
    "governance/permission.py",
    "governance/deny-list.json",
    "governance/mcp-allowlist.json",
    ".claude/settings.json",
    "Security-kit/secret_scan.py",
    "Security-kit/content_trust.py",
    "Harness-Best-Practice/observability/audit_hook.py",
]


def test_write_to_mechanism_and_policy_is_denied():
    """Every mechanism/policy file rejects a plain Write."""
    for target in MECHANISM_AND_POLICY:
        allowed, reason = _check("write_file", {"file_path": target, "content": "x"})
        assert not allowed, f"{target} was writable — S2.4 not enforced"
        assert "S2.4" in reason, f"{target} denied for the wrong reason: {reason}"


def test_all_write_target_fields_are_checked():
    """NotebookEdit uses notebook_path, not file_path — both must be gated."""
    for field in ("file_path", "notebook_path", "path"):
        allowed, _ = _check("write_file", {field: "governance/permission.py"})
        assert not allowed, f"write via '{field}' field bypassed Gate 1b"


# ---------------------------------------------------------------------------
# 2. Evasion by path shape fails
# ---------------------------------------------------------------------------

def test_path_traversal_cannot_evade():
    """'../' and './' forms resolve to the same target and are still denied."""
    evasions = [
        "claims/../governance/permission.py",
        "./governance/permission.py",
        "governance/../governance/permission.py",
        "governance//permission.py",
        "Security-kit/../governance/deny-list.json",
    ]
    for target in evasions:
        allowed, reason = _check("write_file", {"file_path": target})
        assert not allowed, f"traversal evaded Gate 1b: {target}"
        assert "S2.4" in reason


def test_absolute_path_cannot_evade():
    """An absolute path to a protected file is the same file."""
    target = str(PROJECT_ROOT / "governance" / "permission.py")
    allowed, _ = _check("write_file", {"file_path": target})
    assert not allowed, "absolute path evaded Gate 1b"


def test_whitespace_padding_cannot_evade():
    """Leading/trailing whitespace is stripped before resolution."""
    allowed, _ = _check("write_file", {"file_path": "  governance/permission.py  "})
    assert not allowed, "whitespace padding evaded Gate 1b"


# ---------------------------------------------------------------------------
# 3. Policy cannot disable the built-ins
# ---------------------------------------------------------------------------

def test_builtins_survive_policy_deletion():
    """Emptying protected_paths in policy must NOT unprotect the mechanism.

    This is the property that makes S2.4 a *mechanism* guarantee rather than a
    policy suggestion. If an attacker (or a careless edit) strips the key, the
    built-in list still applies.
    """
    original = permission.DENY_LIST_PATH
    with tempfile.TemporaryDirectory() as tmp:
        stripped = Path(tmp) / "deny-list.json"
        stripped.write_text(json.dumps({"patterns": [], "protected_paths": []}))
        try:
            permission.DENY_LIST_PATH = stripped
            allowed, reason = _check(
                "write_file", {"file_path": "governance/permission.py"}
            )
            assert not allowed, "emptying protected_paths disabled S2.4"
            assert "S2.4" in reason
        finally:
            permission.DENY_LIST_PATH = original


def test_missing_deny_list_file_still_protects():
    """A deleted deny-list.json must not unprotect the mechanism either."""
    original = permission.DENY_LIST_PATH
    try:
        permission.DENY_LIST_PATH = Path("/nonexistent/deny-list.json")
        allowed, _ = _check("write_file", {"file_path": "governance/permission.py"})
        assert not allowed, "missing deny-list.json disabled S2.4"
    finally:
        permission.DENY_LIST_PATH = original


def test_policy_can_add_protected_paths():
    """Projects may freeze extra files; the union is enforced."""
    original = permission.DENY_LIST_PATH
    with tempfile.TemporaryDirectory() as tmp:
        extended = Path(tmp) / "deny-list.json"
        extended.write_text(
            json.dumps({"patterns": [], "protected_paths": ["claims/router.py"]})
        )
        try:
            permission.DENY_LIST_PATH = extended
            allowed, _ = _check("write_file", {"file_path": "claims/router.py"})
            assert not allowed, "project-added protected path was not enforced"
        finally:
            permission.DENY_LIST_PATH = original


# ---------------------------------------------------------------------------
# 4. No false positives — ordinary work still proceeds
# ---------------------------------------------------------------------------

def test_ordinary_writes_are_allowed():
    """Gate 1b must not become a general write ban."""
    benign = [
        "claims/router.py",
        "Harness-Best-Practice/progress.md",
        "tests/test_new_thing.py",
        "Context/product-design.md",
        "governance/README.md",
    ]
    for target in benign:
        allowed, reason = _check("write_file", {"file_path": target, "content": "x"})
        assert allowed, f"false positive: {target} blocked ({reason})"


def test_similar_but_distinct_paths_are_allowed():
    """Matching is on the resolved path, not a substring of the name."""
    benign = [
        "governance/permission_test.py",
        "governance/permission.py.bak",
        "docs/governance/permission.py",
        "Security-kit/secret_scan_notes.md",
    ]
    for target in benign:
        allowed, reason = _check("write_file", {"file_path": target})
        assert allowed, f"over-broad match blocked {target} ({reason})"


def test_bash_without_a_path_is_unaffected():
    """A plain shell command carries no write target; Gate 1b abstains."""
    allowed, _ = _check("bash", {"command": "echo hello"})
    assert allowed, "Gate 1b interfered with an ordinary bash call"


def test_missing_and_malformed_input_do_not_crash():
    """Gate 1b must never raise — a crash in the gate is an enforcement outage."""
    for bad in ({}, {"file_path": ""}, {"file_path": None}, {"file_path": 42}):
        allowed, _ = _check("write_file", bad)
        assert allowed is True, f"unexpected denial for {bad!r}"
    assert permission.check_protected_paths("not-a-dict") is None


# ---------------------------------------------------------------------------
# 5. The shell vector — complementary, and honestly partial
# ---------------------------------------------------------------------------

def test_shell_redirect_to_mechanism_is_denied_by_patterns():
    """A file_path check cannot see `> permission.py`; the regex patterns do.

    Uses the REAL deny-list.json, so this also asserts the shipped policy
    actually carries the S2.4 shell patterns.
    """
    commands = [
        "echo x > governance/permission.py",
        "echo x >> governance/deny-list.json",
        "sed -i 's/a/b/' governance/mcp-allowlist.json",
        "tee governance/permission.py",
        "chmod 777 governance/permission.py",
    ]
    for cmd in commands:
        reason = permission.check_deny_list(cmd)
        assert reason is not None, f"shell vector not blocked: {cmd}"


def test_interpreter_write_is_a_known_documented_gap():
    """Pins the residual gap so it cannot silently widen — or silently close.

    An interpreter can open a protected file for writing without using any
    deny-listed shell token, exactly as `python3 -c "import urllib..."` evades the
    egress gate. SECURITY.md S2.4 documents this. This test asserts the *documented*
    state, so if someone later closes the gap the test fails and forces the doc to be
    updated too — a doc that overclaims is the failure mode this whole fix addressed.
    """
    cmd = 'python3 -c \'open("governance/permission.py","w").write("")\''
    reason = permission.check_deny_list(cmd)
    assert reason is None, (
        "The interpreter write vector is now blocked. That is an improvement — "
        "update SECURITY.md S2.4's 'Residual gap' note and this test together."
    )


if __name__ == "__main__":
    failures = []
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except AssertionError as exc:
            failures.append((fn.__name__, str(exc)))
            print(f"  FAIL  {fn.__name__}: {exc}")
    print("-" * 60)
    print(f"Results: {len(tests) - len(failures)} passed, {len(failures)} failed")
    sys.exit(1 if failures else 0)
