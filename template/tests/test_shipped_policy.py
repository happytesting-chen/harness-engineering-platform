"""
Ground-truth tests for the SHIPPED policy — `governance/deny-list.json` itself.

Every other test in this suite targets a *mechanism*: does the gate evaluate
correctly, does the invariant fail when mutated. `test_fixtures.py:25-27`
deliberately substitutes a synthetic `TEST_DENY_LIST` of plain substrings so that
it tests the engine and not the data. That is correct isolation, and it leaves the
shipped patterns untested by construction — so `deny-list.json` enjoyed the
reputation of a green suite that never read it.

This file reads the real policy. It asserts BOTH directions, because a deny-list
fails in two ways and only one of them is usually tested:

  UNDER-BLOCK  a catastrophic command is allowed.       Classic. Everyone tests this.
  OVER-BLOCK   an innocuous command is denied.          Presents as "the agent
               mysteriously cannot list a file", produces no failing test, and
               trains its users to disable the gate.

Both directions have already shipped as live defects here — see the build design
§6.2 items 10 and 11. Item 10 (a `\\s*` that permitted zero separator, so the letters
`tee` inside `steering` were a hit) was found by the gate refusing a read-only `ls`.
Item 11 was found the same way, *after* item 10 was patched.

Runnable with:
    python3 -m pytest tests/test_shipped_policy.py -v
    python3 tests/test_shipped_policy.py
"""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import governance.permission as permission  # noqa: E402

DENY_LIST_PATH = PROJECT_ROOT / "governance" / "deny-list.json"


# ---------------------------------------------------------------------------
# 1. The policy is loadable and is the real one
#
# If this fails, every assertion below is vacuous — which is the whole failure
# mode this file exists to prevent.
# ---------------------------------------------------------------------------

def test_the_shipped_policy_is_the_one_under_test():
    """No monkeypatching. `check_deny_list` must read `governance/deny-list.json`."""
    assert permission.DENY_LIST_PATH == DENY_LIST_PATH, (
        f"check_deny_list reads {permission.DENY_LIST_PATH}, not the shipped policy. "
        "A previous test probably leaked a monkeypatched path."
    )
    data = json.loads(DENY_LIST_PATH.read_text())
    assert data.get("patterns"), "shipped deny-list has no patterns"


# ---------------------------------------------------------------------------
# 2. UNDER-BLOCK: what must never be allowed
#
# Each case names the shipped pattern it exercises, so a deleted pattern produces
# a legible failure rather than a mysterious one.
# ---------------------------------------------------------------------------

MUST_DENY = [
    ("rm -rf / --no-preserve-root", "literal: rm -rf /"),
    ("mkfs.ext4 /dev/sda1", "literal: mkfs"),
    ("cat /etc/hosts > /dev/sda", "literal: > /dev/"),
    ("shutdown -h now", "literal: shutdown"),
    ("reboot", "literal: reboot"),
    ("echo pwned > governance/permission.py", "regex: shell redirect onto the mechanism"),
    ("echo x >> .claude/settings.json", "regex: append onto the hook wiring"),
    ("sed -i 's/exit(2)/exit(0)/' governance/permission.py", "regex: in-place edit"),
    ("perl -i -pe 's/2/0/' governance/deny-list.json", "regex: in-place edit"),
    ("tee governance/mcp-allowlist.json", "regex: tee onto policy"),
    ("dd of=governance/permission.py", "regex: dd onto the mechanism"),
    ("chmod 000 governance/permission.py", "regex: chmod on the mechanism"),
    ("rm Security-kit/secret_scan.py", "regex: rm the secret scanner"),
    ("mv governance/deny-list.json /tmp/", "regex: mv the policy away"),
    # The one case that pins the FIX for item 11 rather than the bug. A backslash
    # before a newline is a line continuation, so this is ONE shell command that
    # writes the mechanism — and the plausible repair (`[^|;&\n]` in the class)
    # takes it from DENY to ALLOW. Without this row, that repair passes the suite.
    ("sed -i \\\n 's/exit(2)/exit(0)/' governance/permission.py",
     "regex: backslash-newline continuation is ONE command"),
]


def test_catastrophic_commands_are_denied():
    """UNDER-BLOCK direction. Deleting any shipped pattern must break this."""
    allowed = [
        (cmd, why) for cmd, why in MUST_DENY
        if permission.check_deny_list(cmd) is None
    ]
    assert not allowed, "shipped deny-list ALLOWED commands it must refuse:\n" + "\n".join(
        f"  {why:48s} {cmd!r}" for cmd, why in allowed
    )


# ---------------------------------------------------------------------------
# 3. OVER-BLOCK: what must never be denied
#
# These are ordinary read-only commands taken from real sessions in this repo.
# Every one of them mentions a protected directory, because that is what makes
# them the hard cases: the gate must distinguish *reading* the mechanism from
# *writing* it. Cases 1 and 2 are the item-10 regression — `s-tee-ring` and
# `guaran-tee` supply the `tee` that a pattern without `\\b` will harvest.
# ---------------------------------------------------------------------------

MUST_ALLOW = [
    ("ls -la kiro/steering/security.md Security-kit/README.md", "item 10: 'steering' contains 'tee'"),
    ("grep -n 'guarantee' Security-kit/SECURITY.md", "item 10: 'guarantee' contains 'tee'"),
    ("wc -l governance/permission.py", "read-only"),
    ("cat governance/deny-list.json", "read-only"),
    ("git diff Security-kit/", "read-only"),
    ("git log --oneline governance/", "read-only"),
    ("python3 tests/test_fixtures.py", "running the suite"),
    ("./init.sh", "the project's own health check"),
    ("sed -n '1,10p' governance/permission.py", "sed WITHOUT -i is a reader"),
    ("awk 'NR<3' governance/deny-list.json", "awk WITHOUT -i is a reader"),
    ("diff governance/deny-list.json /tmp/old.json", "read-only comparison"),
]


def test_ordinary_read_only_commands_are_allowed():
    """OVER-BLOCK direction — the unusual one, and the reason this file exists."""
    denied = [
        (cmd, why, permission.check_deny_list(cmd)) for cmd, why in MUST_ALLOW
        if permission.check_deny_list(cmd) is not None
    ]
    assert not denied, (
        "shipped deny-list DENIED read-only commands. An over-blocking gate is not "
        "'safe by default' — it is a gate its users will switch off:\n"
        + "\n".join(f"  {why:44s} {cmd!r}\n    -> {reason}" for cmd, why, reason in denied)
    )


# ---------------------------------------------------------------------------
# 4. Item 11 — a defect PINNED, not fixed
#
# Same idiom as tests/test_protected_paths.py::test_interpreter_write_is_a_known_
# documented_gap: assert the state the docs describe, so the gap cannot close
# silently and leave a doc overclaiming (or, here, under-claiming).
# ---------------------------------------------------------------------------

# Two commands that are individually allowed (both appear in MUST_ALLOW above),
# joined by a newline — as they are whenever a single Bash call runs two lines.
_COMPOSED = (
    "sed -n '1,10p' governance/permission.py\n"
    "grep -n -i 'gate' .claude/settings.json"
)


def test_newline_composition_is_a_known_documented_defect():
    """Pins build-design §6.2 item 11 until the per-line fix lands.

    Every shipped regex guards its interior with `[^|;&]*`, intended to stop a match
    running across a command boundary. It covers `;` `|` `&` and NOT `\\n`, which is
    equally a separator — so `sed` from line 1 and `-i` plus a protected path from
    line 2 compose into a hit. Joined by `;` instead of a newline, the same two
    commands are allowed; that asymmetry is the proof it is the class, not the intent.

    The fix belongs in `check_deny_list` (unfold backslash-newline continuations,
    split on newlines, match per line) and NOT in the four patterns: adding `\\n` to
    the character class clears the false positive and opens a real bypass, because
    `sed -i` followed by a backslash and a newline is ONE command. See §6.2's
    four-case table.
    """
    assert permission.check_deny_list(_COMPOSED) is not None, (
        "Newline composition no longer false-positives. That is the fix landing — "
        "now flip this test to assert None, move §6.2 item 11 out of the unowned "
        "ledger, and add the four §6.2 cases (including the backslash-newline "
        "continuation, which must still DENY) as ordinary rows above."
    )
    # The same two commands, joined by a real shell separator, are allowed. This
    # half must hold either way — it is what makes the case above a defect rather
    # than a policy decision.
    assert permission.check_deny_list(_COMPOSED.replace("\n", "; ")) is None, (
        "Joined by ';' these two read-only commands are now denied too. The defect "
        "widened from newline composition to plain over-blocking."
    )


# ---------------------------------------------------------------------------
# 5. Item 8 — the reason must reach the agent
#
# Claude Code feeds STDERR back to the model on exit 2 and discards stdout for a
# blocked call. A gate that computes a correct reason and writes it to the wrong
# stream refuses indistinguishably from a gate that crashed. Driving the real CLI
# is the only way to test this; an in-process call to check_deny_list cannot see it.
#
# Note on the second case: it drives secret_scan.py with EMPTY stdin, whose
# documented behaviour is to fail closed. That exercises the same channel — exit 2
# plus a reason on fd 2 — without committing a credential-shaped literal to this
# file. (Writing one here is itself blocked by the very hook under test, which is
# the correct outcome; real credential detection is covered by tests/test_hooks.py.)
# ---------------------------------------------------------------------------

HOOKS = [
    ("permission.py: deny-list hit",
     PROJECT_ROOT / "governance" / "permission.py",
     json.dumps({"tool_name": "Bash",
                 "tool_input": {"command": "rm -rf / --no-preserve-root"}})),
    ("permission.py: malformed payload (fail closed)",
     PROJECT_ROOT / "governance" / "permission.py",
     "not json at all"),
    ("secret_scan.py: empty stdin (fail closed)",
     PROJECT_ROOT / "Security-kit" / "secret_scan.py",
     ""),
]


def test_denial_reasons_go_to_stderr():
    """Both preventive hooks must exit 2 AND explain themselves on fd 2."""
    problems = []
    for label, script, payload in HOOKS:
        proc = subprocess.run(
            [sys.executable, str(script)],
            input=payload, capture_output=True, text=True,
            cwd=str(PROJECT_ROOT), timeout=10,
        )
        if proc.returncode != 2:
            problems.append(
                f"{label}: exit {proc.returncode}, expected 2 — only exit 2 blocks, "
                f"every other outcome silently allows"
            )
            continue
        if not proc.stderr.strip():
            problems.append(
                f"{label}: exit 2 with EMPTY stderr. The agent is told 'no' with no "
                f"reason and cannot tell a refusal from a crash. stdout was: {proc.stdout!r}"
            )
    assert not problems, "\n".join(problems)


# ---------------------------------------------------------------------------
# 6. Refusal coverage — a denial must also be RECORDED
#
# A denied call never reaches PostToolUse, so the observer that logs every allowed
# call cannot see any refusal: the strongest evidence the control produced is the
# evidence nobody keeps. `_deny` therefore records for itself.
#
# In production that record is deliberately best-effort — it sits in a
# `try/except Exception: pass` and exits 2 regardless, because a RECORD must never
# be able to change a GATE's verdict. This test asserts it anyway: best-effort
# describes what happens when logging *fails*, not a licence for the call to be
# absent. Without this assertion, deleting the audit call is invisible.
# ---------------------------------------------------------------------------

AUDIT_LOG = PROJECT_ROOT / "Harness-Best-Practice" / "observability" / "audit.log"


def test_a_denial_is_recorded_not_only_refused():
    """The refusal-coverage half of the gate — see build design §4.2.6 finding 1."""
    before = AUDIT_LOG.read_text() if AUDIT_LOG.exists() else ""
    proc = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "governance" / "permission.py")],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "reboot"}}),
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=10,
    )
    assert proc.returncode == 2, f"expected a denial, got exit {proc.returncode}"
    after = AUDIT_LOG.read_text() if AUDIT_LOG.exists() else ""
    new = after[len(before):].strip()
    assert new, (
        "The denial was refused but not recorded. A denied call never reaches "
        "PostToolUse, so if _deny does not log it, the refusal exists in no record "
        "at all — invisible to the operator at the same moment it is unexplained "
        "to the agent."
    )
    entry = json.loads(new.split("\n")[-1])
    assert entry.get("decision") == "DENIED", f"recorded decision was {entry.get('decision')!r}"
    assert entry.get("reason"), "recorded a denial with no reason"


# ---------------------------------------------------------------------------
# Standalone execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_the_shipped_policy_is_the_one_under_test,
        test_catastrophic_commands_are_denied,
        test_ordinary_read_only_commands_are_allowed,
        test_newline_composition_is_a_known_documented_defect,
        test_denial_reasons_go_to_stderr,
        test_a_denial_is_recorded_not_only_refused,
    ]
    print("Running shipped-policy tests (real governance/deny-list.json)...")
    print("-" * 70)
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL  {t.__name__}\n{exc}")
    print("-" * 70)
    print(f"Results: {len(tests) - failed} passed, {failed} failed, {len(tests)} total")
    sys.exit(1 if failed else 0)
