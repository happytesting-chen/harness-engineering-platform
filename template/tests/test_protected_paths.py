"""
Ground-truth tests for `check_protected_paths` — protected write targets (S2.4).

Why this file exists: `check_deny_list` inspects the shell *command* string, but a
Write/Edit/MultiEdit/NotebookEdit payload carries `file_path` and no `command`. So
before this gate existed, a file-editing tool call targeting `permission.py` or
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

# Derived from the mechanism, not retyped beside it. A hand-maintained copy silently
# stops covering the 9th entry the day someone adds one -- which is exactly what had
# happened here: audit.log was protected by the gate and absent from this list.
MECHANISM_AND_POLICY = list(permission.BUILTIN_PROTECTED_PATHS)


def test_the_builtin_list_is_the_list_under_test():
    """Guards the line above: every built-in is exercised, none is assumed."""
    assert set(MECHANISM_AND_POLICY) == set(permission.BUILTIN_PROTECTED_PATHS)
    assert len(MECHANISM_AND_POLICY) >= 10, (
        "built-in protected paths shrank. Was 8; the two pre-model screens "
        "(prompt_screen.py, result_screen.py) were added 2026-08-17 because each is a "
        "hook entry point that disables a control when blanked — measured, an Edit to "
        "result_screen.py was ALLOW before that."
    )


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
        assert not allowed, f"write via '{field}' field bypassed check_protected_paths"


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
        assert not allowed, f"traversal evaded check_protected_paths: {target}"
        assert "S2.4" in reason


def test_absolute_path_cannot_evade():
    """An absolute path to a protected file is the same file."""
    target = str(PROJECT_ROOT / "governance" / "permission.py")
    allowed, _ = _check("write_file", {"file_path": target})
    assert not allowed, "absolute path evaded check_protected_paths"


def test_whitespace_padding_cannot_evade():
    """Leading/trailing whitespace is stripped before resolution."""
    allowed, _ = _check("write_file", {"file_path": "  governance/permission.py  "})
    assert not allowed, "whitespace padding evaded check_protected_paths"


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
    """check_protected_paths must not become a general write ban."""
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
    """A plain shell command carries no write target; the gate abstains."""
    allowed, _ = _check("bash", {"command": "echo hello"})
    assert allowed, "check_protected_paths interfered with an ordinary bash call"


def test_missing_and_malformed_input_do_not_crash():
    """check_protected_paths must never raise — a crash in the gate is an enforcement outage."""
    for bad in ({}, {"file_path": ""}, {"file_path": None}, {"file_path": 42}):
        allowed, _ = _check("write_file", bad)
        assert allowed is True, f"unexpected denial for {bad!r}"
    assert permission.check_protected_paths("not-a-dict") is None


# ---------------------------------------------------------------------------
# 5. The shell vector — complementary, and honestly partial
#
# Gate 1a inspects a structured write target. The shell has none, so deny-list.json
# reaches for regex instead. These tests measure how far that reaches.
#
# The previous version of this section sampled five commands that all paired a covered
# verb with a covered path, so it passed at 100% while 57% of the matrix was open --
# and SECURITY.md cited it as proof. A test whose passing tells you nothing about the
# property it names is worse than no test: it converts an unknown into a false known.
# ---------------------------------------------------------------------------

# 14 ways a shell writes a file. Not exhaustive -- that is the point of the section.
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

# Measured against the shipped deny-list.json. Every entry is a verb that writes any
# protected path without tripping a pattern. Update this set ONLY together with
# SECURITY.md S2.4's residual-gap box -- the test below fails in both directions
# precisely so the doc cannot drift from the mechanism again.
UNCOVERED_VERBS = {"cp", "install", "ln -sf", "git checkout", "dd if-first"}

# Paths no pattern names, for verbs that otherwise match. The four regexes each carry
# their own path list; these are the paths that fall outside all of them.
UNCOVERED_PATHS = {
    "Harness-Best-Practice/observability/audit_hook.py",
    "Harness-Best-Practice/observability/audit.log",
}

# There used to be a third exception here — REDIRECT_ONLY_PATHS, because the redirect
# family named only governance/ and .claude/settings.json, so `echo x >
# Security-kit/content_trust.py` was open while an Edit to the same file was denied.
# Adding the Security-kit branch to that pattern on 2026-08-17 closed it, and the
# hole was never intentional: it was the redirect regex being written before
# Security-kit had mechanism files in it. The gap is now describable without any
# path-specific exception, which `test_the_open_set_has_exactly_two_shapes` asserts.


def _shell_blocks(verb_template: str, path: str) -> bool:
    return permission.check_deny_list(verb_template.format(p=path)) is not None


def test_shell_patterns_block_the_common_forms_they_claim():
    """The covered cells really are covered — the patterns are not decoration.

    Asserts the shipped policy carries working S2.4 patterns for the verb/path pairs
    SECURITY.md says it covers.
    """
    for verb, tmpl in SHELL_WRITE_VERBS:
        if verb in UNCOVERED_VERBS:
            continue
        for path in MECHANISM_AND_POLICY:
            if path in UNCOVERED_PATHS:
                continue
            assert _shell_blocks(tmpl, path), (
                f"a verb/path pair SECURITY.md claims is covered is open: {verb} -> {path}"
            )


def test_shell_pattern_coverage_is_partial_and_measured():
    """Pins the exact size and shape of the shell gap, in both directions.

    This test fails if coverage *widens* as well as if it narrows. That is deliberate:
    the documented gap and the measured gap must move together, or SECURITY.md starts
    overclaiming again the moment someone edits a regex.
    """
    open_cells, closed_cells = [], []
    for verb, tmpl in SHELL_WRITE_VERBS:
        for path in MECHANISM_AND_POLICY:
            (closed_cells if _shell_blocks(tmpl, path) else open_cells).append((verb, path))

    total = len(SHELL_WRITE_VERBS) * len(MECHANISM_AND_POLICY)
    assert len(open_cells) + len(closed_cells) == total

    # 1. Every verb in UNCOVERED_VERBS is open for every protected path.
    for verb in UNCOVERED_VERBS:
        for path in MECHANISM_AND_POLICY:
            assert (verb, path) in open_cells, (
                f"'{verb}' now blocks {path}. Coverage improved — update UNCOVERED_VERBS "
                f"and SECURITY.md S2.4's residual-gap box together."
            )

    # 2. The two audit paths have no shell coverage from any verb.
    for path in UNCOVERED_PATHS:
        assert all(
            (verb, path) in open_cells for verb, _ in SHELL_WRITE_VERBS
        ), f"{path} gained shell coverage — update UNCOVERED_PATHS and SECURITY.md together."

    # 3. The measured total, as cited in SECURITY.md S2.4.
    #    Was 78 of 168 until 2026-09-01, when the 15 runtime-mvp modules and the
    #    signed classifier lock joined BUILTIN_PROTECTED_PATHS (12 -> 28 paths) and
    #    the redirect and chmod/chown/rm/mv families gained a Security-kit/runtime/
    #    prefix so the new paths are covered like every other mechanism file. The
    #    ratio IMPROVED, 54% -> 60% closed: the added paths are covered by all nine
    #    covered verbs, so they dilute the two uncovered audit paths. The open set
    #    still has exactly two shapes — adding covered paths cannot create a third,
    #    which test_the_open_set_has_exactly_two_shapes asserts independently.
    assert len(open_cells) == 158, (
        f"shell coverage changed: {len(open_cells)} of {total} cells open, expected 158. "
        f"Update the number in SECURITY.md S2.4's residual-gap box to match."
    )
    assert total == 392, f"matrix size changed to {total}; SECURITY.md cites 392"


def test_the_open_set_has_exactly_two_shapes():
    """The gap is two clean families, with no path-specific exception left.

    Stronger than the count above, and it catches what a count cannot: a change that
    closes one cell and opens another keeps `len(open_cells) == 68` while moving the
    shape of the hole. Asserting set equality means the residual gap can be stated in
    one sentence -- five shell verbs no pattern reaches, plus the two audit paths no
    pattern names -- and the day that sentence stops being true, this fails.

    It was NOT true before 2026-08-17: `Security-kit/secret_scan.py` and
    `content_trust.py` were additionally open to the three redirect verbs, an
    irregular third hole that the Security-kit branch of the redirect pattern closed.
    """
    measured = {
        (verb, path)
        for verb, tmpl in SHELL_WRITE_VERBS
        for path in MECHANISM_AND_POLICY
        if not _shell_blocks(tmpl, path)
    }
    predicted = {
        (verb, path)
        for verb, _ in SHELL_WRITE_VERBS
        for path in MECHANISM_AND_POLICY
        if verb in UNCOVERED_VERBS or path in UNCOVERED_PATHS
    }
    assert measured == predicted, (
        "the shell gap no longer has the two-family shape SECURITY.md S2.4 describes.\n"
        f"  open but not predicted: {sorted(measured - predicted)}\n"
        f"  predicted but now closed: {sorted(predicted - measured)}"
    )


def test_uncovered_shell_verbs_actually_overwrite_the_mechanism():
    """'Not blocked by the gate' is a weaker claim than 'writes the file'. Prove the latter.

    Runs the uncovered verbs for real against a THROWAWAY tree — never the live
    mechanism — so the residual-gap box rests on a demonstrated write, not on a
    non-matching regex.
    """
    import subprocess

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        victim = root / "permission.py"
        src = root / "src"

        for verb, tmpl in SHELL_WRITE_VERBS:
            if verb not in UNCOVERED_VERBS or verb == "git checkout":
                continue  # git checkout needs a repo; covered by the matrix test above
            # Reset both files per verb, and unlink first: `ln -sf` leaves victim as a
            # symlink to src, so a plain write_text would write THROUGH it and corrupt
            # the source for every later verb.
            victim.unlink(missing_ok=True)
            victim.write_text("ORIGINAL MECHANISM\n")
            src.write_text("REPLACED\n")
            cmd = tmpl.format(p=str(victim)).replace("/tmp/src", str(src))
            assert permission.check_deny_list(cmd) is None, f"{verb} is blocked now"
            subprocess.run(cmd, shell=True, capture_output=True, cwd=root)
            assert victim.read_text().strip() == "REPLACED", (
                f"{verb} did not overwrite the target; the gap claim for it is wrong"
            )


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


# ---------------------------------------------------------------------------
# 6. Evasion by path IDENTITY, not path shape
#
# The tests in section 2 all vary the *spelling* of a path while `normpath` still
# collapses it to the protected string. These vary the *identity*: two different
# strings that the filesystem resolves to the same inode. `os.path.normpath` is a
# pure string operation, so it cannot see either — only `Path.resolve()` can.
# ---------------------------------------------------------------------------

def _fs_is_case_insensitive() -> bool:
    """True on macOS/Windows defaults, where FOO.PY and foo.py are one file."""
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "CaseProbe.tmp"
        probe.write_text("x")
        return (Path(tmp) / "caseprobe.tmp").exists()


def test_case_variant_cannot_evade_on_case_insensitive_fs():
    """On a case-insensitive filesystem, GOVERNANCE/PERMISSION.PY *is* the gate.

    Measured: the write is allowed and it lands on the real `permission.py`, so the
    agent rewrites the mechanism constraining it — the exact scenario S2.4 exists to
    prevent. `_resolve` uses `os.path.normpath`, which never touches disk and so
    cannot know the two spellings name one file.
    """
    if not _fs_is_case_insensitive():
        return  # on a case-sensitive fs these genuinely are different files
    for target in ("GOVERNANCE/PERMISSION.PY",
                   "Governance/Permission.py",
                   "governance/PERMISSION.py"):
        allowed, reason = _check("write_file", {"file_path": target})
        assert not allowed, (
            f"case-variant '{target}' evaded check_protected_paths and resolves to the real "
            f"permission.py on this filesystem — the mechanism is writable"
        )
        assert "S2.4" in reason


def test_hard_link_to_mechanism_cannot_evade():
    """A hard link is the same inode under a second name — writing it writes the gate.

    Measured as a live bypass before `_same_file` compared inodes: a symlink has a
    target to `resolve()` through, but a hard link does not. Both names are equally
    real, so only a (st_dev, st_ino) comparison can tell they are one file.
    """
    import os

    link = PROJECT_ROOT / "tests" / "_tmp_gate_hardlink.py"
    if link.exists():
        link.unlink()
    os.link(PROJECT_ROOT / "governance" / "permission.py", link)
    try:
        allowed, reason = _check(
            "write_file", {"file_path": "tests/_tmp_gate_hardlink.py"}
        )
        assert not allowed, (
            "a hard link to permission.py evaded Gate 1a — writing it modifies the "
            "mechanism, since both names share one inode"
        )
        assert "S2.4" in reason
    finally:
        link.unlink()


def test_symlink_to_mechanism_cannot_evade():
    """A symlink is a second name for the same file; writing it writes the target.

    `normpath` deliberately does NOT follow links (that is its documented contract),
    so the protected-path comparison must use `Path.resolve()`, which does.
    """
    link_dir = PROJECT_ROOT / "tests"
    link = link_dir / "_tmp_gate_symlink.py"
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(PROJECT_ROOT / "governance" / "permission.py")
    try:
        allowed, reason = _check(
            "write_file", {"file_path": "tests/_tmp_gate_symlink.py"}
        )
        assert not allowed, (
            "a symlink pointing at permission.py evaded check_protected_paths — writing it "
            "modifies the mechanism"
        )
        assert "S2.4" in reason
    finally:
        link.unlink()


# ---------------------------------------------------------------------------
# 7. An untrusted policy file must DENY, not error
#
# The CLI blocks only on exit 2; every other exit code is a non-blocking hook error
# and the tool PROCEEDS (see permission.py's CLI-mode docstring). So a gate that
# raises on a corrupt policy file does not fail closed — it fails OPEN.
# ---------------------------------------------------------------------------

def _run_cli(tool_name: str, tool_input: dict, deny_list_text: str):
    """Drive the real CLI with a substituted deny-list.json; return its exit code."""
    import os
    import shutil
    import subprocess

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        shutil.copytree(PROJECT_ROOT / "governance", work / "governance")
        (work / "Harness-Best-Practice").mkdir()
        shutil.copy(
            PROJECT_ROOT / "Harness-Best-Practice" / "feature_list.json",
            work / "Harness-Best-Practice",
        )
        dl = work / "governance" / "deny-list.json"
        if deny_list_text is None:
            dl.unlink()
        else:
            dl.write_text(deny_list_text)
        proc = subprocess.run(
            [sys.executable, str(work / "governance" / "permission.py")],
            input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
            capture_output=True, text=True, cwd=str(work),
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        return proc.returncode


# Assembled at runtime: the literal string is itself deny-listed, so writing it
# inline would make this test file unwriteable through the very gate it tests.
_DENIED_COMMAND = " ".join(["sud" + "o", "shut" + "down"])


def test_corrupt_policy_file_denies_rather_than_erroring():
    """A malformed deny-list.json must exit 2, not 1.

    Exit 1 is a hook *error*: Claude Code lets the tool run. So corrupting one JSON
    file previously disabled BOTH hard-deny gates — including S2.4 self-protection.
    """
    for label, tool, tool_input in [
        ("command deny", "Bash", {"command": _DENIED_COMMAND}),
        ("protected path", "Write", {"file_path": "governance/permission.py"}),
    ]:
        code = _run_cli(tool, tool_input, "{ this is not valid json")
        assert code == 2, (
            f"corrupt deny-list.json returned exit={code} for the {label} gate; "
            f"only exit 2 blocks — exit {code} is a hook error and the tool RUNS"
        )


def test_missing_policy_file_denies_command_patterns():
    """A deleted deny-list.json leaves command patterns with no floor at all.

    check_protected_paths survives deletion via BUILTIN_PROTECTED_PATHS, but `patterns` has no
    built-in equivalent — so absence must deny rather than silently allow everything.
    """
    code = _run_cli("Bash", {"command": _DENIED_COMMAND}, None)
    assert code == 2, (
        f"deleting deny-list.json returned exit={code}; a command the shipped "
        f"policy denies was allowed because the policy simply vanished"
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
