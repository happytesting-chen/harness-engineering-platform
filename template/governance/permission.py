"""
Generic permission gate — the foundation layer.
Sits OUTSIDE the model. The model cannot see, edit, or route around this.

Three gates, evaluated in order (fail-closed):
  1a. Hard deny — write targets (BUILTIN_PROTECTED_PATHS, plus any additions in
      deny-list.json `protected_paths`). Enforces S2.4: the agent may not edit
      the mechanism or policy that constrains it. Runs first because it is the
      only gate with a built-in floor, so it still returns a specific verdict
      when the policy file is unreadable.
  1b. Hard deny — command patterns (deny-list.json `patterns`).
  2.  Phase gate (checks feature_list.json — is this tool allowed in this phase?)
  3.  Egress control (default-deny outbound to unlisted hosts).

An unreadable or unparseable policy file raises PolicyError, which CLI mode turns
into exit 2. That is load-bearing, not defensive habit: Claude Code blocks only on
exit 2, and treats every other non-zero as a non-blocking hook error that lets the
tool RUN. A gate that crashed on a corrupt JSON file would therefore fail OPEN.

To customise: edit deny-list.json and governance/mcp-allowlist.json.
Do NOT modify this file per project — it's the mechanism, not the policy.
"""
import json
import os
import re
from pathlib import Path

# Layout: <project_root>/governance/permission.py
#   deny-list.json + mcp-allowlist.json are siblings (in governance/)
#   feature_list.json lives in <project_root>/Harness-Best-Practice/
PROJECT_ROOT = Path(__file__).parent.parent
DENY_LIST_PATH = Path(__file__).parent / "deny-list.json"
ALLOWLIST_PATH = Path(__file__).parent / "mcp-allowlist.json"
FEATURE_LIST_PATH = PROJECT_ROOT / "Harness-Best-Practice" / "feature_list.json"


def _probe_case_insensitive() -> bool:
    try:
        this = Path(__file__)
        swapped = this.with_name(this.name.upper())
        return swapped != this and swapped.exists()
    except OSError:
        return False


_FS_CASE_INSENSITIVE = _probe_case_insensitive()


class PolicyError(RuntimeError):
    """Policy exists but cannot be trusted -> no verdict -> caller must DENY."""


def _same_file(a: Path, b: Path) -> bool:
    """Do two paths name the same file? Compares IDENTITY, not spelling.

    Three cases defeat a pure string comparison, and each is a real bypass:
      - a symlink is a second name for the same file (handled by `_resolve`);
      - a HARD link is the same inode under another name, with nothing to resolve
        through — only a stat comparison sees it;
      - on a case-insensitive filesystem, GOVERNANCE/PERMISSION.PY *is* permission.py.

    `os.path.samefile` compares (st_dev, st_ino), which covers the first two. It
    requires both paths to exist, so the string comparison remains the fallback for
    a target that a Write is about to create.
    """
    if a == b:
        return True
    try:
        if os.path.samefile(a, b):
            return True
    except OSError:
        pass  # a target being created does not exist yet; fall through
    return _FS_CASE_INSENSITIVE and str(a).casefold() == str(b).casefold()


def _load_json(path, *, required=False):
    try:
        text = path.read_text()
    except FileNotFoundError:
        if required:
            raise PolicyError(f"policy file missing: {path.name} (fail closed)")
        return {}
    except OSError as exc:
        raise PolicyError(f"policy file unreadable: {path.name} ({exc.strerror})")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        raise PolicyError(f"policy file is not valid JSON: {path.name} (fail closed)")
    if not isinstance(data, dict):
        raise PolicyError(f"policy file is not a JSON object: {path.name}")
    return data


def check_deny_list(command: str) -> str | None:
    """Gate 1b: hard deny on command patterns. Reason if denied, None if allowed.

    Raises PolicyError if deny-list.json is missing or unparseable: unlike Gate 1a
    there is no built-in floor for `patterns`, so an absent policy would mean
    "nothing is denied". The caller converts that to a denial.

    Each entry in `patterns` is either:
      - a string  → substring match (backward-compatible default), or
      - an object  {"pattern": "...", "mode": "substring"|"word"|"regex"}
          * "word"  → matches the literal only on word boundaries, so "curl" does not
                       fire on "curly"; the fix for the naive-substring problem.
          * "regex" → full regex match.
    A malformed regex falls back to substring match rather than crashing the gate.
    """
    data = _load_json(DENY_LIST_PATH, required=True)
    for entry in data.get("patterns", []):
        if isinstance(entry, dict):
            pat = entry.get("pattern", "")
            mode = entry.get("mode", "substring")
        else:
            pat, mode = entry, "substring"
        if not pat:
            continue
        try:
            if mode == "word":
                hit = re.search(rf"\b{re.escape(pat)}\b", command) is not None
            elif mode == "regex":
                hit = re.search(pat, command) is not None
            else:
                hit = pat in command
        except re.error:
            hit = pat in command  # bad regex → safe fallback, never crash the gate
        if hit:
            return f"deny-list hit: '{pat}'"
    return None


# Write-target fields used by Claude Code's file-editing tools. A Write/Edit call
# carries no "command", so the command-pattern loop above cannot see it — these are
# where the *target* of a write lives.
WRITE_TARGET_FIELDS = ("file_path", "notebook_path", "path")

# Enforced even if deny-list.json omits `protected_paths` or is missing entirely.
# S2.4 is a mechanism guarantee, so it must not be silently removable by editing
# policy — that would be the very bypass this gate exists to prevent.
BUILTIN_PROTECTED_PATHS = (
    "governance/permission.py",
    "governance/deny-list.json",
    "governance/mcp-allowlist.json",
    ".claude/settings.json",
    "Security-kit/secret_scan.py",
    "Security-kit/content_trust.py",
    "Harness-Best-Practice/observability/audit_hook.py",
    "Harness-Best-Practice/observability/audit.log",
)


def _resolve(path_str: str) -> Path:
    """Reduce a path to one comparable absolute form.

    Two steps, because each catches a different evasion. `os.path.normpath`
    collapses "../", "./" and "//" as a pure string operation, so
    "claims/../governance/permission.py" cannot smuggle a write past the check.
    `Path.resolve()` then follows symlinks, so a link pointing at the mechanism is
    recognised as the mechanism — normpath deliberately does not do this.

    `resolve()` tolerates a non-existent target (we are judging a file that a Write
    may be about to create); on OSError we keep the normalized form rather than
    give up, so the gate degrades to string comparison instead of abstaining.
    """
    raw = os.path.expanduser(path_str.strip())
    p = Path(raw)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    normalised = Path(os.path.normpath(str(p)))
    try:
        return normalised.resolve()
    except OSError:
        return normalised


def check_protected_paths(tool_input: dict) -> str | None:
    """Gate 1a: block writes that target the harness's own mechanism or policy.

    Implements S2.4. `check_deny_list` only inspects shell command strings, so a
    Write/Edit/MultiEdit/NotebookEdit call — whose payload carries `file_path`
    rather than `command` — was previously invisible to every gate. That let the
    agent rewrite `permission.py` or `deny-list.json`, i.e. edit its own
    constraints. This closes that path.

    Matching is on the *identity* of the target, not its spelling: `_resolve`
    collapses `../`, `./` and absolute forms and follows symlinks, and `_same_file`
    additionally treats case variants as equal on a case-insensitive filesystem
    (macOS/Windows), where `GOVERNANCE/PERMISSION.PY` really is `permission.py`.
    A pure string comparison misses both of those.

    Never raises: the built-in list is enforced even when `deny-list.json` is
    missing, so this gate can always answer. That is why it runs before Gate 1b —
    a deleted policy file must not cost S2.4 its specific verdict. Nothing is
    swallowed, because Gate 1b reads the same file and denies on it.

    Returns a reason string if denied, None if allowed.
    """
    if not isinstance(tool_input, dict):
        return None

    targets = [tool_input.get(f) for f in WRITE_TARGET_FIELDS]
    targets = [t for t in targets if isinstance(t, str) and t.strip()]
    if not targets:
        return None

    data = _load_json(DENY_LIST_PATH)
    configured = data.get("protected_paths", [])
    if not isinstance(configured, list):
        configured = []
    # Union, never override: policy may ADD protected paths but cannot remove the
    # built-ins. Mechanism guarantees are not up for negotiation by policy.
    patterns = list(BUILTIN_PROTECTED_PATHS) + [
        p for p in configured if isinstance(p, str) and p.strip()
    ]

    for target in targets:
        resolved = _resolve(target)
        for rel in patterns:
            if _same_file(resolved, _resolve(rel)):
                return f"protected path (S2.4): refusing to write '{rel}'"
    return None


def check_phase_gate(tool_name: str) -> str | None:
    """Gate 2: is this tool allowed in the current active phase?
    Reads feature_list.json to find the active phase, then checks
    mcp-allowlist.json for phase-gated tools."""
    features = _load_json(FEATURE_LIST_PATH).get("features", [])
    active = [f for f in features if f.get("status") == "active"]
    if not active:
        # No active phase. Distinguish two cases:
        #   (a) STEADY-STATE — every phase is "passing". Feature work is complete
        #       and human-signed-off; the harness should keep operating, not brick.
        #       Deny-list and egress remain enforced by their own gates; any
        #       phase-gated tool's `gated_until` phase is by definition passing,
        #       so its gate is satisfied. Fall through to the allowlist check.
        #   (b) UNDEFINED — some phase is not-started/other. State is genuinely
        #       ambiguous; fail closed.
        if features and all(f.get("status") == "passing" for f in features):
            pass  # steady-state; continue to allowlist/gate check below
        else:
            return "no active phase — cannot determine tool permissions"

    allowlist = _load_json(ALLOWLIST_PATH)
    for tool in allowlist.get("tools", []):
        if tool["name"] == tool_name:
            if "gated_until" in tool:
                required_phase = tool["gated_until"]
                # Check if required phase is passing
                for f in features:
                    if f["id"] == required_phase and f.get("status") != "passing":
                        return f"{tool_name} gated until {required_phase} is passing"
            return None  # tool found and not gated (or gate satisfied)
    return f"{tool_name} not in allowlist"


def check_egress(command: str) -> str | None:
    """Gate 3: default-deny outbound network access."""
    network_tokens = ["curl ", "wget ", "nc ", "ssh ", "nmap "]
    if not any(tok in command for tok in network_tokens):
        return None
    allowlist = _load_json(ALLOWLIST_PATH)
    allowed_hosts = allowlist.get("egress_hosts", [])
    if any(host in command for host in allowed_hosts):
        return None
    return "default-deny egress: target host not on allowlist"


def make_permission_check(auto_deny_on_ask=True):
    """Returns a permission_check(block) -> (allowed: bool, reason: str)."""
    def permission_check(block):
        tool_input = block.input if isinstance(block.input, dict) else {}
        cmd = tool_input.get("command", "")
        tool = block.name

        # Gate 1a: hard deny — write targets (S2.4). Runs FIRST and for every
        # tool: a write can arrive as Write/Edit/MultiEdit/NotebookEdit or as an
        # MCP tool carrying a path, and none of those carry a "command".
        # Ordered before the command patterns deliberately: this gate has a
        # built-in floor (BUILTIN_PROTECTED_PATHS) and so still answers when the
        # policy file is missing, whereas check_deny_list must raise. Keeping it
        # first means a deleted policy file cannot cost us S2.4's specific verdict.
        reason = check_protected_paths(tool_input)
        if reason:
            return False, reason

        # Gate 1b: hard deny — command patterns (raises if policy unreadable)
        reason = check_deny_list(cmd)
        if reason:
            return False, reason

        # Gate 2: phase gate
        reason = check_phase_gate(tool)
        if reason:
            return False, reason

        # Gate 3: egress
        if tool == "bash":
            reason = check_egress(cmd)
            if reason:
                return False, reason

        return True, ""
    return permission_check


# --- CLI mode (for .claude/settings.json hooks) ---
#
# Claude Code delivers the tool call as a JSON envelope on stdin, e.g.
#   {"tool_name": "Bash", "tool_input": {"command": "..."}, ...extra keys...}
# and blocks the action ONLY on exit code 2. Any other non-zero is treated as a
# non-blocking hook error and the tool proceeds — so this path must FAIL CLOSED
# (exit 2) on malformed or empty input, never crash out with exit 1.
#
# Claude's tool names are PascalCase (Bash, Write, Edit); the allowlist and egress
# check use internal lowercase names (bash, write_file). Normalize before checking.

# Maps Claude Code tool names to the internal names used in mcp-allowlist.json.
TOOL_NAME_MAP = {
    "Bash": "bash",
    "Write": "write_file",
    "Edit": "write_file",
    "MultiEdit": "write_file",
    "NotebookEdit": "write_file",
}


def normalize_tool_name(name: str) -> str:
    """Map a Claude Code tool name to its internal allowlist name.
    Unmapped names pass through unchanged (already-internal or MCP tools)."""
    return TOOL_NAME_MAP.get(name, name)


if __name__ == "__main__":
    import sys

    def _deny(reason: str):
        print(reason)
        sys.exit(2)

    # Read tool call from stdin. Empty or unparseable input FAILS CLOSED.
    raw = sys.stdin.read().strip()
    if not raw:
        _deny("permission gate: empty stdin (fail closed)")
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        _deny("permission gate: malformed hook payload (fail closed)")
    if not isinstance(data, dict):
        _deny("permission gate: unexpected hook payload shape (fail closed)")

    tool_input = data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        tool_input = {}

    # Build a minimal Block-like object for the check
    class _Block:
        def __init__(self, name, input):
            self.name = name
            self.input = input

    block = _Block(normalize_tool_name(data.get("tool_name", "")), tool_input)
    check = make_permission_check()
    try:
        allowed, reason = check(block)
    except PolicyError as exc:
        _deny(f"permission gate: {exc}")
    except Exception as exc:  # noqa: BLE001
        _deny(f"permission gate: internal error ({type(exc).__name__}) (fail closed)")
    if not allowed:
        _deny(reason)
    sys.exit(0)
