"""
Generic permission gate — the foundation layer.
Sits OUTSIDE the model. The model cannot see, edit, or route around this.

Three gates, evaluated in order (fail-closed):
  1. Hard deny-list (loaded from deny-list.json)
  2. Phase gate (checks feature_list.json — is this tool allowed in the current phase?)
  3. Egress control (default-deny outbound to unlisted hosts)

To customise: edit deny-list.json and governance/mcp-allowlist.json.
Do NOT modify this file per project — it's the mechanism, not the policy.
"""
import json
import re
from pathlib import Path

# Layout: <project_root>/governance/permission.py
#   deny-list.json + mcp-allowlist.json are siblings (in governance/)
#   feature_list.json lives in <project_root>/Harness-Best-Practice/
PROJECT_ROOT = Path(__file__).parent.parent
DENY_LIST_PATH = Path(__file__).parent / "deny-list.json"
ALLOWLIST_PATH = Path(__file__).parent / "mcp-allowlist.json"
FEATURE_LIST_PATH = PROJECT_ROOT / "Harness-Best-Practice" / "feature_list.json"


def _load_json(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def check_deny_list(command: str) -> str | None:
    """Gate 1: hard deny. Returns reason string if denied, None if allowed.

    Each entry in `patterns` is either:
      - a string  → substring match (backward-compatible default), or
      - an object  {"pattern": "...", "mode": "substring"|"word"|"regex"}
          * "word"  → matches the literal only on word boundaries, so "curl" does not
                       fire on "curly"; the fix for the naive-substring problem.
          * "regex" → full regex match.
    A malformed regex falls back to substring match rather than crashing the gate.
    """
    data = _load_json(DENY_LIST_PATH)
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
        cmd = block.input.get("command", "")
        tool = block.name

        # Gate 1: hard deny
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
    allowed, reason = check(block)
    if not allowed:
        _deny(reason)
    sys.exit(0)
