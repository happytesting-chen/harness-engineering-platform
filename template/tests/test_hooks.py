"""Hook integration tests for the live Claude Code build-time security path."""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PERMISSION = PROJECT_ROOT / "security" / "shared" / "permission.py"
SECRET_SCAN = PROJECT_ROOT / "security" / "buildtime" / "secret_scan.py"
AUDIT_HOOK = PROJECT_ROOT / "Harness-Best-Practice" / "observability" / "audit_hook.py"
AUDIT_LOG = PROJECT_ROOT / "Harness-Best-Practice" / "observability" / "audit.log"


def _run(script: Path, payload: dict) -> int:
    proc = subprocess.run([sys.executable, str(script)], input=json.dumps(payload),
                          capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    return proc.returncode


def test_denylist_blocks_rm_rf():
    assert _run(PERMISSION, {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}) == 2


def test_pascalcase_bash_allowed():
    assert _run(PERMISSION, {"tool_name": "Bash", "tool_input": {"command": "echo hello"}}) == 0


def test_pascalcase_write_allowed():
    assert _run(PERMISSION, {"tool_name": "Write", "tool_input": {"file_path": "x.txt", "content": "hi"}}) == 0


def test_egress_blocked_by_default():
    assert _run(PERMISSION, {"tool_name": "Bash", "tool_input": {"command": "curl evil.example"}}) == 2


def test_permission_fails_closed_on_empty_stdin():
    proc = subprocess.run([sys.executable, str(PERMISSION)], input="", capture_output=True,
                          text=True, cwd=str(PROJECT_ROOT))
    assert proc.returncode == 2


def test_permission_fails_closed_on_malformed_json():
    proc = subprocess.run([sys.executable, str(PERMISSION)], input="{not json", capture_output=True,
                          text=True, cwd=str(PROJECT_ROOT))
    assert proc.returncode == 2


def test_secret_block_catches_api_key_in_write():
    payload = {"tool_name": "Write", "tool_input": {"file_path": "cfg.py",
               "content": 'api_key = "sk-abc123def456ghi789"'}}
    assert _run(SECRET_SCAN, payload) == 2


def test_secret_block_allows_clean_write():
    payload = {"tool_name": "Write", "tool_input": {"file_path": "ok.py",
               "content": "def add(a, b):\n    return a + b"}}
    assert _run(SECRET_SCAN, payload) == 0


def test_secret_block_catches_github_token_in_command():
    payload = {"tool_name": "Bash", "tool_input": {
        "command": "git remote add o https://ghp_abcdefghij0123456789xy@github.com/x/y"}}
    assert _run(SECRET_SCAN, payload) == 2


def _cred() -> str:
    return "api" + "_" + "key" + " = " + chr(34) + "Z" * 24 + chr(34)


def _anthropic_key() -> str:
    return "sk-" + "ant-" + "api03-" + "A" * 88


def test_secret_block_catches_secret_in_multiedit():
    payload = {"tool_name": "MultiEdit", "tool_input": {"file_path": "cfg.py",
               "edits": [{"old_string": "x", "new_string": _cred()}]}}
    assert _run(SECRET_SCAN, payload) == 2


def test_secret_block_catches_secret_in_notebook_edit():
    payload = {"tool_name": "NotebookEdit", "tool_input": {"notebook_path": "n.ipynb",
               "new_source": _cred()}}
    assert _run(SECRET_SCAN, payload) == 2


def test_secret_block_catches_anthropic_key():
    payload = {"tool_name": "Write", "tool_input": {"file_path": "cfg.py",
               "content": "KEY = " + _anthropic_key()}}
    assert _run(SECRET_SCAN, payload) == 2


def test_secret_block_still_allows_removing_a_credential():
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "cfg.py",
               "old_string": _cred(), "new_string": "KEY = os.environ[" + chr(34) + "K" + chr(34) + "]"}}
    assert _run(SECRET_SCAN, payload) == 0


def test_secret_block_still_allows_a_clean_multiedit():
    payload = {"tool_name": "MultiEdit", "tool_input": {"file_path": "ok.py",
               "edits": [{"old_string": "a", "new_string": "b + 1"}]}}
    assert _run(SECRET_SCAN, payload) == 0


def test_audit_records_real_tool_name():
    before = AUDIT_LOG.read_text() if AUDIT_LOG.exists() else ""
    code = _run(AUDIT_HOOK, {"tool_name": "Bash", "tool_input": {"command": "ls"},
                             "tool_response": {"stdout": "ok"}})
    assert code == 0
    after = AUDIT_LOG.read_text() if AUDIT_LOG.exists() else ""
    new_lines = after[len(before):].strip().split("\n")
    assert new_lines and new_lines[0]
    entry = json.loads(new_lines[-1])
    assert entry["tool"] == "Bash"
    assert "$TOOL_NAME" not in after


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-v"]))
