"""
Hook Integration Test — the layer the unit/E2E tests never exercised.

test_fixtures.py and test_e2e.py call make_permission_check() as a Python API,
which bypasses the shell hook wiring in .claude/settings.json. That is why the
Claude Code enforcement path could be completely broken while every test stayed
green. This test drives the ACTUAL hook scripts the way Claude Code drives them:
a JSON envelope on stdin, blocking only on exit code 2.

Run:
    python3 tests/test_hooks.py
    python3 -m pytest tests/test_hooks.py -v
"""
import json
import subprocess
import sys
from pathlib import Path

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent
PERMISSION = TEMPLATE_ROOT / "governance" / "permission.py"
SECRET_SCAN = TEMPLATE_ROOT / "governance" / "secret_scan.py"
AUDIT_HOOK = TEMPLATE_ROOT / "observability" / "audit_hook.py"
AUDIT_LOG = TEMPLATE_ROOT / "observability" / "audit.log"


def _run(script: Path, payload: dict) -> int:
    """Pipe a Claude-shaped envelope to a hook script; return its exit code.
    Run from TEMPLATE_ROOT so relative paths inside the scripts resolve."""
    proc = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True, text=True, cwd=str(TEMPLATE_ROOT),
    )
    return proc.returncode


# --- governance-check (permission.py) -------------------------------------

def test_denylist_blocks_rm_rf():
    code = _run(PERMISSION, {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}})
    assert code == 2, "deny-list must block rm -rf / (exit 2)"


def test_pascalcase_bash_allowed():
    """Regression: 'Bash' must normalize to 'bash' and pass the allowlist."""
    code = _run(PERMISSION, {"tool_name": "Bash", "tool_input": {"command": "echo hello"}})
    assert code == 0, "harmless echo via PascalCase 'Bash' must be allowed (exit 0)"


def test_pascalcase_write_allowed():
    code = _run(PERMISSION, {"tool_name": "Write",
                             "tool_input": {"file_path": "x.txt", "content": "hi"}})
    assert code == 0, "'Write' must normalize to 'write_file' and be allowed"


def test_egress_blocked_by_default():
    code = _run(PERMISSION, {"tool_name": "Bash",
                             "tool_input": {"command": "curl evil.example"}})
    assert code == 2, "curl to non-allowlisted host must be blocked"


def test_permission_fails_closed_on_empty_stdin():
    proc = subprocess.run([sys.executable, str(PERMISSION)], input="",
                          capture_output=True, text=True, cwd=str(TEMPLATE_ROOT))
    assert proc.returncode == 2, "empty stdin must FAIL CLOSED (exit 2), not open"


def test_permission_fails_closed_on_malformed_json():
    proc = subprocess.run([sys.executable, str(PERMISSION)], input="{not json",
                          capture_output=True, text=True, cwd=str(TEMPLATE_ROOT))
    assert proc.returncode == 2, "malformed payload must FAIL CLOSED (exit 2)"


# --- secret-block (secret_scan.py) ----------------------------------------

def test_secret_block_catches_api_key_in_write():
    """The decoded-content case the old inline regex missed."""
    code = _run(SECRET_SCAN, {"tool_name": "Write",
                              "tool_input": {"file_path": "cfg.py",
                                             "content": 'api_key = "sk-abc123def456ghi789"'}})
    assert code == 2, "hardcoded api_key in file content must be blocked"


def test_secret_block_allows_clean_write():
    code = _run(SECRET_SCAN, {"tool_name": "Write",
                              "tool_input": {"file_path": "ok.py",
                                             "content": "def add(a, b):\n    return a + b"}})
    assert code == 0, "clean content must pass"


def test_secret_block_catches_github_token_in_command():
    code = _run(SECRET_SCAN, {"tool_name": "Bash",
                              "tool_input": {"command": "git remote add o https://ghp_abcdefghij0123456789xy@github.com/x/y"}})
    assert code == 2, "GitHub token in a bash command must be blocked"


# --- audit-capture (audit_hook.py) ----------------------------------------

def test_audit_records_real_tool_name():
    """Regression: audit line must contain the real tool name, not '$TOOL_NAME' or ''."""
    before = AUDIT_LOG.read_text() if AUDIT_LOG.exists() else ""
    code = _run(AUDIT_HOOK, {"tool_name": "Bash", "tool_input": {"command": "ls"},
                             "tool_response": {"stdout": "ok"}})
    assert code == 0, "audit hook must never block (exit 0)"
    after = AUDIT_LOG.read_text() if AUDIT_LOG.exists() else ""
    new_lines = after[len(before):].strip().split("\n")
    assert new_lines and new_lines[0], "audit hook wrote no line"
    entry = json.loads(new_lines[-1])
    assert entry["tool"] == "Bash", f"expected real tool name, got {entry['tool']!r}"
    assert "$TOOL_NAME" not in after, "literal $TOOL_NAME must never appear in the log"


if __name__ == "__main__":
    try:
        import pytest
        sys.exit(pytest.main([__file__, "-v"]))
    except ImportError:
        tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
        passed = failed = 0
        for t in tests:
            try:
                t()
                print(f"  \033[32m✓ PASS\033[0m  {t.__name__}")
                passed += 1
            except AssertionError as e:
                print(f"  \033[31m✗ FAIL\033[0m  {t.__name__}: {e}")
                failed += 1
        print(f"\nResults: {passed} passed, {failed} failed, {passed+failed} total")
        sys.exit(1 if failed else 0)
