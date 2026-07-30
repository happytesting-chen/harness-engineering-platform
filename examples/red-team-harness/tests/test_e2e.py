"""
End-to-End Enforcement Test — Day 4 Pattern.

Validates Requirements 9.1–9.5:
  9.1  Runs a complete agent session through the REAL Agent Loop with the REAL Permission Gate.
  9.2  Denied call confirmed NOT executed (side effects absent).
  9.3  Allowed call confirmed DID execute (side effects present).
  9.4  Removing enforcement causes the test to FAIL — proving sensitivity to enforcement wiring.
  9.5  Passing test output serves as evidence the gate PREVENTS execution, not just logs denial.

Usage:
    python3 -m pytest tests/test_e2e.py -v
    python3 tests/test_e2e.py
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# --- Path setup: allow imports from sibling directories ---
TEMPLATE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TEMPLATE_ROOT))

from demo.fake_model import Block, Response, FakeModel
from demo.harness import agent_loop, TOOL_HANDLERS, WORKDIR
from governance.permission import make_permission_check


# ---------------------------------------------------------------------------
# Test policy setup/teardown helpers
# ---------------------------------------------------------------------------

# We store original file contents so we can restore after tests.
_ORIGINALS = {}

# Paths that get test-specific content during tests
_DENY_LIST = TEMPLATE_ROOT / "governance" / "deny-list.json"
_ALLOWLIST = TEMPLATE_ROOT / "tools" / "mcp-allowlist.json"
_FEATURE_LIST = TEMPLATE_ROOT / "feature_list.json"
_AUDIT_LOG = TEMPLATE_ROOT / "observability" / "audit.log"


def _backup(path: Path):
    """Save original content (or note file doesn't exist)."""
    if path.exists():
        _ORIGINALS[str(path)] = path.read_text()
    else:
        _ORIGINALS[str(path)] = None


def _restore(path: Path):
    """Restore original content or remove file if it didn't exist."""
    key = str(path)
    if key in _ORIGINALS:
        if _ORIGINALS[key] is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(_ORIGINALS[key])


def setup_test_policy():
    """Write deterministic test-specific policy files."""
    _backup(_DENY_LIST)
    _backup(_ALLOWLIST)
    _backup(_FEATURE_LIST)
    _backup(_AUDIT_LOG)

    # Deny-list: block dangerous patterns
    _DENY_LIST.write_text(json.dumps({
        "patterns": ["rm -rf /", "sudo"]
    }))

    # Allowlist: bash is ungated, write_file is ungated
    _ALLOWLIST.write_text(json.dumps({
        "tools": [
            {"name": "bash", "version": "1.0", "description": "Shell commands"},
            {"name": "write_file", "version": "1.0", "description": "Write files"}
        ],
        "egress_hosts": ["localhost"]
    }))

    # Feature list: phase-01 is active (required for phase-gate to pass)
    _FEATURE_LIST.write_text(json.dumps({
        "project": "e2e-test",
        "features": [
            {
                "id": "phase-01",
                "name": "Testing Phase",
                "description": "E2E test phase",
                "dependencies": [],
                "status": "active",
                "verification": "true",
                "evidence": ""
            }
        ]
    }))

    # Clear audit log for clean assertions
    _AUDIT_LOG.unlink(missing_ok=True)

    # Clean sandbox
    if WORKDIR.exists():
        shutil.rmtree(WORKDIR)
    WORKDIR.mkdir(exist_ok=True)


def teardown_test_policy():
    """Restore original policy files and clean up test artifacts."""
    _restore(_DENY_LIST)
    _restore(_ALLOWLIST)
    _restore(_FEATURE_LIST)
    _restore(_AUDIT_LOG)

    # Clean sandbox
    if WORKDIR.exists():
        shutil.rmtree(WORKDIR)
    WORKDIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Test 1: Denied call does NOT execute (side effects absent)
# Validates: Req 9.1, 9.2, 9.5
# ---------------------------------------------------------------------------

def test_denied_call_not_executed():
    """
    A denied tool call (rm -rf /) must NOT produce side effects.
    The permission gate blocks execution AND the audit log records DENIED.
    """
    setup_test_policy()
    try:
        # Create a canary file in sandbox — if 'rm -rf /' somehow executes,
        # this file would be deleted.
        canary = WORKDIR / "canary.txt"
        canary.write_text("I must survive")

        # Script: model requests a denied command, then says done.
        script = [
            Response(
                content=[Block(type="tool_use", name="bash",
                               input={"command": "rm -rf /"}, id="call_deny_1")],
                stop_reason="tool_use",
            ),
            Response(
                content=[Block(type="text", text="Done.")],
                stop_reason="end_turn",
            ),
        ]
        model = FakeModel(script)
        gate = make_permission_check()

        # Run through real agent loop with real permission gate (Req 9.1)
        agent_loop([], model, permission_check=gate, max_turns=5)

        # ASSERT: canary file survives — side effects absent (Req 9.2)
        assert canary.exists(), (
            "FAIL: canary.txt was deleted — denied call executed! "
            "Permission gate did NOT prevent execution."
        )
        assert canary.read_text() == "I must survive", (
            "FAIL: canary.txt was modified — denied call had side effects!"
        )

        # ASSERT: audit log shows DENIED (Req 9.5 — evidence)
        assert _AUDIT_LOG.exists(), "Audit log was not created"
        log_lines = _AUDIT_LOG.read_text().strip().split("\n")
        denied_entries = [json.loads(line) for line in log_lines
                         if json.loads(line).get("decision") == "DENIED"]
        assert len(denied_entries) >= 1, (
            "FAIL: No DENIED entry in audit log — gate not recording denials"
        )
        assert "rm -rf /" in denied_entries[0].get("reason", ""), (
            "FAIL: Denial reason doesn't mention the blocked pattern"
        )

    finally:
        teardown_test_policy()


# ---------------------------------------------------------------------------
# Test 2: Allowed call DOES execute (side effects present)
# Validates: Req 9.1, 9.3, 9.5
# ---------------------------------------------------------------------------

def test_allowed_call_executed():
    """
    An allowed tool call (write_file) must produce its side effect.
    The file must exist in sandbox/ after the loop completes.
    """
    setup_test_policy()
    try:
        target_file = "e2e_proof.txt"
        target_content = "enforcement test passed"

        # Script: model requests an allowed write_file call, then says done.
        script = [
            Response(
                content=[Block(type="tool_use", name="write_file",
                               input={"path": target_file,
                                       "content": target_content},
                               id="call_allow_1")],
                stop_reason="tool_use",
            ),
            Response(
                content=[Block(type="text", text="File written.")],
                stop_reason="end_turn",
            ),
        ]
        model = FakeModel(script)
        gate = make_permission_check()

        # Run through real agent loop with real permission gate (Req 9.1)
        agent_loop([], model, permission_check=gate, max_turns=5)

        # ASSERT: file was created — side effect present (Req 9.3)
        written = WORKDIR / target_file
        assert written.exists(), (
            f"FAIL: {target_file} not found in sandbox — allowed call did NOT execute!"
        )
        assert written.read_text() == target_content, (
            f"FAIL: {target_file} has wrong content — tool handler produced unexpected output"
        )

        # ASSERT: audit log shows ALLOWED (Req 9.5 — evidence)
        assert _AUDIT_LOG.exists(), "Audit log was not created"
        log_lines = _AUDIT_LOG.read_text().strip().split("\n")
        allowed_entries = [json.loads(line) for line in log_lines
                          if json.loads(line).get("decision") == "ALLOWED"]
        assert len(allowed_entries) >= 1, (
            "FAIL: No ALLOWED entry in audit log"
        )

    finally:
        teardown_test_policy()


# ---------------------------------------------------------------------------
# Test 3: Removing enforcement causes the dangerous call to EXECUTE
# Validates: Req 9.4 — Day 4 pattern proof
# ---------------------------------------------------------------------------

def test_removing_enforcement_allows_dangerous_call():
    """
    Day 4 pattern: run the SAME denied-call scenario but with
    permission_check=None (no gate). The dangerous call now EXECUTES,
    proving that our enforcement test above is sensitive to the wiring.

    This test ASSERTS that without the gate, the "dangerous" side effect
    IS present — which means if we accidentally removed the gate from
    the real path, test_denied_call_not_executed() would catch it.
    """
    setup_test_policy()
    try:
        # Instead of rm -rf /, we use a command whose side effect we can safely
        # observe: writing a marker file via bash 'echo > file'.
        marker = "unguarded_execution.txt"
        dangerous_command = f"echo PROOF > {marker}"

        # First, verify this command IS in our test deny-list for completeness
        # (it isn't — but that's the point: even without deny-list match,
        # the test demonstrates that permission_check=None skips ALL gates).

        # Actually, let's use a more direct proof: we use a command that WOULD
        # be blocked by the deny-list (contains "rm -rf /"), but since there's
        # NO permission_check, it executes anyway.
        # However, we can't actually run rm -rf / in tests safely!
        #
        # Better approach: use write_file tool with permission_check=None to
        # prove any call goes through. Then show that a DENIED-by-policy call
        # also goes through when gate is removed. We'll use a bash command that
        # writes a marker, and add a custom deny pattern so the command IS denied
        # when the gate is present, but executes when the gate is absent.

        # Write a deny-list that blocks our marker command
        _DENY_LIST.write_text(json.dumps({
            "patterns": ["rm -rf /", "sudo", "PROOF"]
        }))

        # Script: model requests a command containing "PROOF" (in deny-list)
        script = [
            Response(
                content=[Block(type="tool_use", name="bash",
                               input={"command": dangerous_command},
                               id="call_nogate_1")],
                stop_reason="tool_use",
            ),
            Response(
                content=[Block(type="text", text="Done.")],
                stop_reason="end_turn",
            ),
        ]

        # --- Phase A: WITH gate, command is denied, marker NOT created ---
        model = FakeModel(script)
        gate = make_permission_check()
        agent_loop([], model, permission_check=gate, max_turns=5)

        marker_path = WORKDIR / marker
        assert not marker_path.exists(), (
            "Precondition failed: marker file exists even with gate active — "
            "deny-list should have blocked the command"
        )

        # Clear audit log between runs
        _AUDIT_LOG.unlink(missing_ok=True)

        # --- Phase B: WITHOUT gate, same command EXECUTES (Req 9.4) ---
        model.reset()
        agent_loop([], model, permission_check=None, max_turns=5)

        assert marker_path.exists(), (
            "FAIL: Removing enforcement did NOT allow the command to execute. "
            "This means the test is NOT sensitive to enforcement wiring — "
            "the Day 4 pattern is broken."
        )
        assert "PROOF" in marker_path.read_text(), (
            "FAIL: Marker file exists but content is wrong — command didn't "
            "execute as expected without the gate."
        )

    finally:
        teardown_test_policy()


# ---------------------------------------------------------------------------
# Entry point for direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Support both pytest and direct execution
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        # Fallback: run tests manually without pytest
        tests = [
            test_denied_call_not_executed,
            test_allowed_call_executed,
            test_removing_enforcement_allows_dangerous_call,
        ]
        passed = 0
        failed = 0
        for test_fn in tests:
            try:
                test_fn()
                print(f"  \033[32m✓ PASS\033[0m  {test_fn.__name__}")
                passed += 1
            except AssertionError as e:
                print(f"  \033[31m✗ FAIL\033[0m  {test_fn.__name__}: {e}")
                failed += 1
            except Exception as e:
                print(f"  \033[31m✗ ERROR\033[0m {test_fn.__name__}: {type(e).__name__}: {e}")
                failed += 1

        print(f"\n{'='*60}")
        print(f"Results: {passed} passed, {failed} failed, {passed+failed} total")
        if failed > 0:
            sys.exit(1)
        print("\n[Day 4 Enforcement Evidence] All E2E tests pass —")
        print("the Permission Gate PREVENTS execution, not just logs denial.")
