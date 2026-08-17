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
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from demo.fake_model import Block, Response, FakeModel
from demo.harness import agent_loop, TOOL_HANDLERS, WORKDIR
import governance.permission as permission
from governance.permission import make_permission_check


# ---------------------------------------------------------------------------
# Test policy setup/teardown helpers
# ---------------------------------------------------------------------------

# We store original file contents so we can restore after tests.
_ORIGINALS = {}

# The gate reads these three as MODULE GLOBALS at call time (permission.py:31-34),
# so setup_test_policy() rebinds them at a scratch directory instead of writing the
# shipped policy. Item 17: writing the real files bumped their mtimes past
# progress.md and moved init.sh's own warning count between runs. The audit log
# stays where it is — it is a .log, outside init.sh's staleness scan, and the
# assertions read it directly.
_REAL_DENY_LIST = permission.DENY_LIST_PATH
_REAL_ALLOWLIST = permission.ALLOWLIST_PATH
_REAL_FEATURE_LIST = permission.FEATURE_LIST_PATH

_TMP_POLICY = None      # scratch dir, created per setup, removed per teardown
_DENY_LIST = None       # bound by setup_test_policy() to the scratch copies
_ALLOWLIST = None
_FEATURE_LIST = None
_AUDIT_LOG = PROJECT_ROOT / "Harness-Best-Practice" / "observability" / "audit.log"


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
    """Write deterministic test-specific policy files.

    Self-cleaning on failure (item 17, finding 1): everything below runs
    inside a try/except. If tempfile.mkdtemp() or any of the write_text()
    calls raises partway through, permission.DENY_LIST_PATH / ALLOWLIST_PATH /
    FEATURE_LIST_PATH have already been rebound to the scratch dir by this
    point. Without the except below, that rebinding — and the scratch dir
    itself — would survive the exception for the rest of the interpreter
    process: every later test exercising the real gate would get a spurious
    "policy file missing" instead of testing the real policy, and the
    directory would leak. teardown_test_policy() undoes exactly that
    (restores the three permission.*_PATH names, restores this module's own
    globals, removes the scratch dir), so calling it here and re-raising is
    sufficient — the caller's own try/finally still sees the exception and
    still fails the test.
    """
    global _TMP_POLICY, _DENY_LIST, _ALLOWLIST, _FEATURE_LIST
    try:
        _TMP_POLICY = Path(tempfile.mkdtemp(prefix="e2e-policy-"))
        _DENY_LIST = _TMP_POLICY / "deny-list.json"
        _ALLOWLIST = _TMP_POLICY / "mcp-allowlist.json"
        _FEATURE_LIST = _TMP_POLICY / "feature_list.json"
        permission.DENY_LIST_PATH = _DENY_LIST
        permission.ALLOWLIST_PATH = _ALLOWLIST
        permission.FEATURE_LIST_PATH = _FEATURE_LIST
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
    except Exception:
        teardown_test_policy()
        raise


def teardown_test_policy():
    """Restore original policy files and clean up test artifacts.

    Also doubles as setup_test_policy()'s own failure-cleanup path (item 17,
    finding 1) — safe to call even if setup only got partway through, since
    every step here is a no-op when there is nothing to undo (_restore() is a
    no-op if _backup() was never reached; the rmtree is a no-op if
    _TMP_POLICY is still None).
    """
    global _TMP_POLICY, _DENY_LIST, _ALLOWLIST, _FEATURE_LIST
    permission.DENY_LIST_PATH = _REAL_DENY_LIST
    permission.ALLOWLIST_PATH = _REAL_ALLOWLIST
    permission.FEATURE_LIST_PATH = _REAL_FEATURE_LIST
    _restore(_AUDIT_LOG)
    if _TMP_POLICY is not None:
        shutil.rmtree(_TMP_POLICY, ignore_errors=True)
        _TMP_POLICY = None
    _DENY_LIST = None
    _ALLOWLIST = None
    _FEATURE_LIST = None

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
# Test 4: the suite does not mutate the tree it is verifying (item 17)
# ---------------------------------------------------------------------------

def test_suite_does_not_touch_the_real_policy_files():
    """The E2E suite must not write the shipped policy files.

    Measured 2026-08-15 on a clean tree: three consecutive `./init.sh` runs
    reported 1, then 2, then 2 warnings. setup_test_policy() rewrote
    governance/*.json byte-identically but with fresh mtimes, and init.sh's
    staleness check scans every *.py/*.json/*.md against progress.md. A test
    that mutates the tree it verifies makes the verifier's output depend on
    run order — and these three files are policy, which nothing but a human
    should be writing.
    """
    real = [
        PROJECT_ROOT / "governance" / "deny-list.json",
        PROJECT_ROOT / "governance" / "mcp-allowlist.json",
        PROJECT_ROOT / "Harness-Best-Practice" / "feature_list.json",
    ]
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in real}

    # Run all three policy-mutating tests inside the snapshot window — each
    # calls setup_test_policy()/teardown_test_policy(), the helpers shared by
    # the whole suite, and test_removing_enforcement_allows_dangerous_call()
    # additionally rewrites the deny-list mid-test. This catches a regression
    # reintroduced into those shared helpers or into these three tests; it
    # does NOT catch a future test that bypasses the helpers and writes a
    # real policy path directly — that would need a suite-wide mechanism,
    # which is out of scope here.
    test_denied_call_not_executed()
    test_allowed_call_executed()
    test_removing_enforcement_allows_dangerous_call()

    for p, snapshot in before.items():
        assert (p.read_bytes(), p.stat().st_mtime_ns) == snapshot, (
            f"FAIL: {p.relative_to(PROJECT_ROOT)} was rewritten by the E2E suite "
            f"(item 17 — content and mtime must both be untouched)"
        )


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
            test_suite_does_not_touch_the_real_policy_files,
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
