"""
Generic permission gate — the foundation layer.
Sits OUTSIDE the model. The model cannot see, edit, or route around this.

Three gates, evaluated in order (fail-closed):
  1. Hard deny-list (loaded from deny-list.json)
  2. Phase gate (checks feature_list.json — is this tool allowed in the current phase?)
  3. Egress control (default-deny outbound to unlisted hosts)

To customise: edit deny-list.json and tools/mcp-allowlist.json.
Do NOT modify this file per project — it's the mechanism, not the policy.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DENY_LIST_PATH = Path(__file__).parent / "deny-list.json"
FEATURE_LIST_PATH = ROOT / "feature_list.json"
ALLOWLIST_PATH = ROOT / "tools" / "mcp-allowlist.json"


def _load_json(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def check_deny_list(command: str) -> str | None:
    """Gate 1: hard deny. Returns reason string if denied, None if allowed."""
    data = _load_json(DENY_LIST_PATH)
    for pattern in data.get("patterns", []):
        if pattern in command:
            return f"deny-list hit: '{pattern}'"
    return None


def check_phase_gate(tool_name: str) -> str | None:
    """Gate 2: is this tool allowed in the current active phase?
    Reads feature_list.json to find the active phase, then checks
    mcp-allowlist.json for phase-gated tools."""
    features = _load_json(FEATURE_LIST_PATH).get("features", [])
    active = [f for f in features if f.get("status") == "active"]
    if not active:
        return "no active phase — cannot determine tool permissions"
    current_phase = active[0]["id"]

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
if __name__ == "__main__":
    import sys

    # Read tool call from stdin (JSON: {"tool_name": "...", "tool_input": {...}})
    raw = sys.stdin.read().strip()
    if not raw:
        sys.exit(0)
    data = json.loads(raw)

    # Build a minimal Block-like object for the check
    class _Block:
        def __init__(self, name, input):
            self.name = name
            self.input = input

    block = _Block(data.get("tool_name", ""), data.get("tool_input", {}))
    check = make_permission_check()
    allowed, reason = check(block)
    if not allowed:
        print(reason)
        sys.exit(2)
    sys.exit(0)
