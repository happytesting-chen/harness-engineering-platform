"""
Data-driven test runner for the Red Team Permission Gate.

Reads tests/fixtures.json, sets up test-specific policy files matching
the red team domain, runs each case through the real Permission Gate,
and asserts the decision matches the expected outcome.

Runnable with:
    python3 -m pytest tests/test_fixtures.py -v
    python3 tests/test_fixtures.py
"""
import json
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Test-specific policy data matching what the red team fixtures.json expects:
#   - deny-list: DoS patterns, lateral movement, reverse shells
#   - mcp-allowlist: bash, nmap, write_file ungated; metasploit gated_until "recon"
#   - feature_list: recon phase is "active" (not "passing")
#   - egress_hosts: 10.20.0.0/24, 10.20.1.0/24, 192.168.100.0/24, localhost
# ---------------------------------------------------------------------------

TEST_DENY_LIST = {
    "patterns": [
        "rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "> /dev/",
        ":(){ :|:& };:", "-Pn 172.16.", "-Pn 10.0.", "hping3",
        "slowloris", "--flood", "scp ",
        "exfil", "nc -e", "nc -c"
    ]
}

TEST_ALLOWLIST = {
    "tools": [
        {"name": "bash", "description": "Shell commands", "version": "1.0"},
        {"name": "nmap", "description": "Network scanning", "version": "7.94"},
        {"name": "write_file", "description": "Write files", "version": "1.0"},
        {
            "name": "metasploit",
            "description": "Exploitation framework",
            "version": "6.3",
            "gated_until": "recon",
        },
    ],
    "egress_hosts": ["10.20.0.", "10.20.1.", "192.168.100.", "localhost", "127.0.0.1"],
}

TEST_FEATURE_LIST = {
    "project": "Red Team Test",
    "features": [
        {
            "id": "scope-validation",
            "name": "Scope Validation",
            "description": "Validate targets",
            "dependencies": [],
            "status": "passing",
            "verification": "true",
            "evidence": "done",
        },
        {
            "id": "recon",
            "name": "Reconnaissance",
            "description": "Active but not passing",
            "dependencies": ["scope-validation"],
            "status": "active",
            "verification": "true",
            "evidence": "",
        },
    ],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES_PATH = Path(__file__).parent / "fixtures.json"


def load_fixtures():
    """Load test cases from fixtures.json."""
    with open(FIXTURES_PATH) as f:
        data = json.load(f)
    return data["cases"]


class Block:
    """Minimal Block-like object for the Permission Gate."""

    def __init__(self, name: str, input_data: dict):
        self.name = name
        self.input = input_data


# ---------------------------------------------------------------------------
# Test runner using monkeypatching to override policy file paths
# ---------------------------------------------------------------------------


def _setup_test_policies(tmp_dir: Path):
    """Write test-specific policy files and return paths."""
    deny_path = tmp_dir / "deny-list.json"
    allowlist_path = tmp_dir / "mcp-allowlist.json"
    feature_path = tmp_dir / "feature_list.json"

    deny_path.write_text(json.dumps(TEST_DENY_LIST))
    allowlist_path.write_text(json.dumps(TEST_ALLOWLIST))
    feature_path.write_text(json.dumps(TEST_FEATURE_LIST))

    return deny_path, allowlist_path, feature_path


def run_fixture_tests():
    """
    Run all fixture cases through the real Permission Gate.
    Uses temporary test-specific policy files and patches path constants.
    Returns (passed: int, failed: int, failures: list).
    """
    import importlib

    # Ensure governance module is importable
    governance_dir = Path(__file__).resolve().parent.parent / "governance"
    if str(governance_dir.parent) not in sys.path:
        sys.path.insert(0, str(governance_dir.parent))

    import governance.permission as permission_mod

    cases = load_fixtures()
    passed = 0
    failed = 0
    failures = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        deny_path, allowlist_path, feature_path = _setup_test_policies(tmp_path)

        # Monkeypatch the path constants in the permission module
        original_deny = permission_mod.DENY_LIST_PATH
        original_allowlist = permission_mod.ALLOWLIST_PATH
        original_feature = permission_mod.FEATURE_LIST_PATH

        try:
            permission_mod.DENY_LIST_PATH = deny_path
            permission_mod.ALLOWLIST_PATH = allowlist_path
            permission_mod.FEATURE_LIST_PATH = feature_path

            check = permission_mod.make_permission_check()

            for i, case in enumerate(cases, 1):
                block = Block(case["tool"], case["input"])
                allowed, reason = check(block)

                actual_decision = "ALLOWED" if allowed else "DENIED"
                expected_decision = case["expected_decision"]

                if actual_decision != expected_decision:
                    failed += 1
                    failure_info = {
                        "case_number": i,
                        "description": case["description"],
                        "expected_decision": expected_decision,
                        "actual_decision": actual_decision,
                        "expected_reason": case.get("expected_reason", ""),
                        "actual_reason": reason,
                    }
                    failures.append(failure_info)
                else:
                    # Verify reason contains expected substring when denied
                    expected_reason = case.get("expected_reason", "")
                    if (
                        expected_decision == "DENIED"
                        and expected_reason
                        and expected_reason not in reason
                    ):
                        failed += 1
                        failure_info = {
                            "case_number": i,
                            "description": case["description"],
                            "expected_decision": expected_decision,
                            "actual_decision": actual_decision,
                            "expected_reason": expected_reason,
                            "actual_reason": reason,
                            "note": "Decision matched but reason mismatch",
                        }
                        failures.append(failure_info)
                    else:
                        passed += 1

        finally:
            # Restore original paths
            permission_mod.DENY_LIST_PATH = original_deny
            permission_mod.ALLOWLIST_PATH = original_allowlist
            permission_mod.FEATURE_LIST_PATH = original_feature

    return passed, failed, failures


# ---------------------------------------------------------------------------
# pytest integration
# ---------------------------------------------------------------------------


def test_all_fixture_cases():
    """
    Pytest-compatible test: runs all fixture cases and reports failures clearly.
    """
    passed, failed, failures = run_fixture_tests()

    if failures:
        msg_lines = [f"\n{'='*60}", f"FIXTURE TEST FAILURES: {failed} of {passed + failed} cases failed", f"{'='*60}"]
        for f in failures:
            msg_lines.append(f"\n  Case #{f['case_number']}: {f['description']}")
            msg_lines.append(f"    Expected: {f['expected_decision']} (reason contains: '{f['expected_reason']}')")
            msg_lines.append(f"    Actual:   {f['actual_decision']} (reason: '{f['actual_reason']}')")
            if "note" in f:
                msg_lines.append(f"    Note:     {f['note']}")
        msg_lines.append(f"\n{'='*60}")
        assert False, "\n".join(msg_lines)


# ---------------------------------------------------------------------------
# Standalone execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running Red Team Permission Gate fixture tests...")
    print("-" * 60)

    passed, failed, failures = run_fixture_tests()

    cases = load_fixtures()
    for i, case in enumerate(cases, 1):
        failure = next((f for f in failures if f["case_number"] == i), None)
        if failure:
            print(f"  FAIL  Case #{i}: {case['description']}")
            print(f"        Expected: {failure['expected_decision']} | Actual: {failure['actual_decision']}")
            print(f"        Expected reason: '{failure['expected_reason']}' | Actual: '{failure['actual_reason']}'")
        else:
            print(f"  PASS  Case #{i}: {case['description']}")

    print("-" * 60)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")

    if failed > 0:
        sys.exit(1)
    else:
        print("\nAll fixture tests passed!")
        sys.exit(0)
