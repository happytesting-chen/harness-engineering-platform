"""Ground-truth tests for S2.4 protected write targets after the security-layer migration.

Historical measurements are retained where they describe the old layout, but every live
path/assertion below targets security/{buildtime,runtime,shared}.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "security" / "shared"))
import permission  # noqa: E402


class Block:
    def __init__(self, name: str, input_data: dict):
        self.name = name
        self.input = input_data


def _check(tool: str, tool_input: dict):
    return permission.make_permission_check()(Block(tool, tool_input))


MECHANISM_AND_POLICY = list(permission.BUILTIN_PROTECTED_PATHS)


def test_the_builtin_list_is_the_list_under_test():
    assert set(MECHANISM_AND_POLICY) == set(permission.BUILTIN_PROTECTED_PATHS)
    assert len(MECHANISM_AND_POLICY) >= 10


def test_write_to_mechanism_and_policy_is_denied():
    for target in MECHANISM_AND_POLICY:
        allowed, reason = _check("write_file", {"file_path": target, "content": "x"})
        assert not allowed, f"{target} was writable — S2.4 not enforced"
        assert "S2.4" in reason


def test_all_write_target_fields_are_checked():
    for field in ("file_path", "notebook_path", "path"):
        allowed, _ = _check("write_file", {field: "security/shared/permission.py"})
        assert not allowed


def test_path_traversal_cannot_evade():
    evasions = [
        "claims/../security/shared/permission.py",
        "./security/shared/permission.py",
        "security/shared/../shared/permission.py",
        "security//shared//permission.py",
        "security/runtime/../shared/deny-list.json",
    ]
    for target in evasions:
        allowed, reason = _check("write_file", {"file_path": target})
        assert not allowed, f"traversal evaded check_protected_paths: {target}"
        assert "S2.4" in reason


def test_absolute_path_cannot_evade():
    target = str(PROJECT_ROOT / "security" / "shared" / "permission.py")
    allowed, _ = _check("write_file", {"file_path": target})
    assert not allowed


def test_whitespace_padding_cannot_evade():
    allowed, _ = _check("write_file", {"file_path": "  security/shared/permission.py  "})
    assert not allowed


def test_builtins_survive_policy_deletion():
    original = permission.DENY_LIST_PATH
    with tempfile.TemporaryDirectory() as tmp:
        stripped = Path(tmp) / "deny-list.json"
        stripped.write_text(json.dumps({"patterns": [], "protected_paths": []}))
        try:
            permission.DENY_LIST_PATH = stripped
            allowed, reason = _check("write_file", {"file_path": "security/shared/permission.py"})
            assert not allowed and "S2.4" in reason
        finally:
            permission.DENY_LIST_PATH = original


def test_missing_deny_list_file_still_protects():
    original = permission.DENY_LIST_PATH
    try:
        permission.DENY_LIST_PATH = Path("/nonexistent/deny-list.json")
        allowed, _ = _check("write_file", {"file_path": "security/shared/permission.py"})
        assert not allowed
    finally:
        permission.DENY_LIST_PATH = original


def test_policy_can_add_protected_paths():
    original = permission.DENY_LIST_PATH
    with tempfile.TemporaryDirectory() as tmp:
        extended = Path(tmp) / "deny-list.json"
        extended.write_text(json.dumps({"patterns": [], "protected_paths": ["claims/router.py"]}))
        try:
            permission.DENY_LIST_PATH = extended
            allowed, _ = _check("write_file", {"file_path": "claims/router.py"})
            assert not allowed
        finally:
            permission.DENY_LIST_PATH = original


def test_ordinary_writes_are_allowed():
    benign = [
        "claims/router.py",
        "Harness-Best-Practice/progress.md",
        "tests/test_new_thing.py",
        "Context/product-design.md",
        "security/README-notes.md",
    ]
    for target in benign:
        allowed, reason = _check("write_file", {"file_path": target, "content": "x"})
        assert allowed, f"false positive: {target} blocked ({reason})"


def test_similar_but_distinct_paths_are_allowed():
    benign = [
        "security/shared/permission_test.py",
        "security/shared/permission.py.bak",
        "docs/security/shared/permission.py",
        "security/buildtime/secret_scan_notes.md",
    ]
    for target in benign:
        allowed, reason = _check("write_file", {"file_path": target})
        assert allowed, f"over-broad match blocked {target} ({reason})"


def test_bash_without_a_path_is_unaffected():
    allowed, _ = _check("bash", {"command": "echo hello"})
    assert allowed


def test_missing_and_malformed_input_do_not_crash():
    for bad in ({}, {"file_path": ""}, {"file_path": None}, {"file_path": 42}):
        allowed, _ = _check("write_file", bad)
        assert allowed is True
    assert permission.check_protected_paths("not-a-dict") is None


SHELL_WRITE_VERBS = [
    ("redirect", "echo x > {p}"),
    ("append", "echo x >> {p}"),
    ("cat-redirect", "cat /tmp/src > {p}"),
    ("cp", "cp /tmp/src {p}"),
    ("install", "install /tmp/src {p}"),
    ("mv", "mv /tmp/src {p}"),
    ("rm", "rm {p}"),
    ("tee", "tee {p} < /tmp/src"),
    ("truncate", "truncate -s 0 {p}"),
    ("sed -i", "sed -i '' s/a/b/ {p}"),
    ("chmod", "chmod 777 {p}"),
    ("ln -sf", "ln -sf /tmp/src {p}"),
    ("git checkout", "git checkout HEAD~1 -- {p}"),
    ("dd if-first", "dd if=/tmp/src of={p}"),
]
UNCOVERED_VERBS = {"cp", "install", "ln -sf", "git checkout", "dd if-first"}
UNCOVERED_PATHS = {
    "security/runtime/__init__.py",
    "Harness-Best-Practice/observability/audit_hook.py",
    "Harness-Best-Practice/observability/audit.log",
}


def _shell_blocks(tmpl: str, path: str) -> bool:
    return permission.check_deny_list(tmpl.format(p=path)) is not None


def test_shell_patterns_block_the_common_forms_they_claim():
    for verb, tmpl in SHELL_WRITE_VERBS:
        if verb in UNCOVERED_VERBS:
            continue
        for path in MECHANISM_AND_POLICY:
            if path in UNCOVERED_PATHS:
                continue
            assert _shell_blocks(tmpl, path), f"claimed shell coverage is open: {verb} -> {path}"


def test_shell_pattern_coverage_is_partial_and_measured():
    open_cells = [
        (verb, path)
        for verb, tmpl in SHELL_WRITE_VERBS
        for path in MECHANISM_AND_POLICY
        if not _shell_blocks(tmpl, path)
    ]
    total = len(SHELL_WRITE_VERBS) * len(MECHANISM_AND_POLICY)
    predicted = {
        (verb, path)
        for verb, _ in SHELL_WRITE_VERBS
        for path in MECHANISM_AND_POLICY
        if verb in UNCOVERED_VERBS or path in UNCOVERED_PATHS
    }
    assert set(open_cells) == predicted
    # Historical pre-migration measurement was 158/392. The migrated tree adds
    # protected implementation/adapter paths, so the live matrix is intentionally
    # re-baselined rather than pretending the old count still describes this layout.
    assert len(open_cells) == 182, f"shell coverage changed: {len(open_cells)} of {total} open"
    assert total == 434, f"matrix size changed to {total}"


def test_uncovered_shell_verbs_actually_overwrite_the_mechanism():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        victim = root / "permission.py"
        src = root / "src"
        for verb, tmpl in SHELL_WRITE_VERBS:
            if verb not in UNCOVERED_VERBS or verb == "git checkout":
                continue
            victim.unlink(missing_ok=True)
            victim.write_text("ORIGINAL MECHANISM\n")
            src.write_text("REPLACED\n")
            cmd = tmpl.format(p=str(victim)).replace("/tmp/src", str(src))
            assert permission.check_deny_list(cmd) is None
            subprocess.run(cmd, shell=True, capture_output=True, cwd=root)
            assert victim.read_text().strip() == "REPLACED"


def test_interpreter_write_is_a_known_documented_gap():
    cmd = 'python3 -c \'open("security/shared/permission.py","w").write("")\''
    assert permission.check_deny_list(cmd) is None


def _fs_is_case_insensitive() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "CaseProbe.tmp"
        probe.write_text("x")
        return (Path(tmp) / "caseprobe.tmp").exists()


def test_case_variant_cannot_evade_on_case_insensitive_fs():
    if not _fs_is_case_insensitive():
        return
    for target in (
        "SECURITY/SHARED/PERMISSION.PY",
        "Security/Shared/Permission.py",
        "security/shared/PERMISSION.py",
    ):
        allowed, reason = _check("write_file", {"file_path": target})
        assert not allowed and "S2.4" in reason


def test_hard_link_to_mechanism_cannot_evade():
    link = PROJECT_ROOT / "tests" / "_tmp_gate_hardlink.py"
    link.unlink(missing_ok=True)
    os.link(PROJECT_ROOT / "security" / "shared" / "permission.py", link)
    try:
        allowed, reason = _check("write_file", {"file_path": "tests/_tmp_gate_hardlink.py"})
        assert not allowed and "S2.4" in reason
    finally:
        link.unlink()


def test_symlink_to_mechanism_cannot_evade():
    link = PROJECT_ROOT / "tests" / "_tmp_gate_symlink.py"
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(PROJECT_ROOT / "security" / "shared" / "permission.py")
    try:
        allowed, reason = _check("write_file", {"file_path": "tests/_tmp_gate_symlink.py"})
        assert not allowed and "S2.4" in reason
    finally:
        link.unlink()


def _run_cli(tool_name: str, tool_input: dict, deny_list_text: str | None):
    import shutil
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shared = work / "security" / "shared"
        shared.parent.mkdir(parents=True)
        shutil.copytree(PROJECT_ROOT / "security" / "shared", shared)
        (work / "Harness-Best-Practice").mkdir()
        shutil.copy(PROJECT_ROOT / "Harness-Best-Practice" / "feature_list.json", work / "Harness-Best-Practice")
        dl = shared / "deny-list.json"
        if deny_list_text is None:
            dl.unlink()
        else:
            dl.write_text(deny_list_text)
        proc = subprocess.run(
            [sys.executable, str(shared / "permission.py")],
            input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
            capture_output=True, text=True, cwd=str(work),
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        return proc.returncode


_DENIED_COMMAND = " ".join(["sud" + "o", "shut" + "down"])


def test_corrupt_policy_file_denies_rather_than_erroring():
    for tool, tool_input in [
        ("Bash", {"command": _DENIED_COMMAND}),
        ("Write", {"file_path": "security/shared/permission.py"}),
    ]:
        assert _run_cli(tool, tool_input, "{ this is not valid json") == 2


def test_missing_policy_file_denies_command_patterns():
    assert _run_cli("Bash", {"command": _DENIED_COMMAND}, None) == 2


if __name__ == "__main__":
    raise SystemExit(__import__("pytest").main([__file__, "-v"]))
