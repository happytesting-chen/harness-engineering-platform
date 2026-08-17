#!/usr/bin/env python3
"""
Demo Script — Scripted 5-turn enforcement demonstration.

Shows the harness enforcing controls in real time:
  Turn 1: Allowed tool call (in allowlist, phase active) → ✓ execute
  Turn 2: Phase-gated tool (prereq not passing) → ⛔ DENIED
  Turn 3: Phase transition (prereq set to "passing")
  Turn 4: Re-request previously-gated tool → ✓ now executes
  Turn 5: Model says "done" → exit

Usage:
    python3 demo/demo.py            # With enforcement
    python3 demo/demo.py --nogate   # Same model, no enforcement

Requirements: zero — uses FakeModel, no API keys or network.
"""
import json
import sys
from pathlib import Path

# --- Path setup ---
DEMO_DIR = Path(__file__).parent
TEMPLATE_ROOT = DEMO_DIR.parent
sys.path.insert(0, str(TEMPLATE_ROOT))
sys.path.insert(0, str(DEMO_DIR))
sys.path.insert(0, str(TEMPLATE_ROOT / "governance"))
sys.path.insert(0, str(TEMPLATE_ROOT / "observability"))

from fake_model import Block, Response, FakeModel
from harness import agent_loop, TOOL_HANDLERS, WORKDIR
import governance.permission as permission_mod
from observability.audit import LOG as AUDIT_LOG_PATH

# --- Demo policy setup ---
# Write deterministic demo policy files so the demo is self-contained.

DENY_LIST_PATH = TEMPLATE_ROOT / "governance" / "deny-list.json"
ALLOWLIST_PATH = TEMPLATE_ROOT / "tools" / "mcp-allowlist.json"
FEATURE_LIST_PATH = TEMPLATE_ROOT / "feature_list.json"

DEMO_DENY_LIST = {
    "patterns": ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "> /dev/"]
}

DEMO_ALLOWLIST = {
    "tools": [
        {"name": "bash", "description": "Shell commands", "version": "1.0"},
        {"name": "write_file", "description": "Write files", "version": "1.0"},
        {
            "name": "exploit_runner",
            "description": "Run exploitation framework",
            "version": "2.0",
            "gated_until": "phase-01",
        },
    ],
    "egress_hosts": ["localhost", "127.0.0.1"],
}

DEMO_FEATURE_LIST_INITIAL = {
    "project": "demo-project",
    "description": "Demonstration of phase-gated enforcement",
    "features": [
        {
            "id": "phase-01",
            "name": "Reconnaissance",
            "description": "Initial recon phase",
            "dependencies": [],
            "status": "active",
            "verification": "true",
            "evidence": "",
        },
        {
            "id": "phase-02",
            "name": "Exploitation",
            "description": "Exploit phase (gated until recon passes)",
            "dependencies": ["phase-01"],
            "status": "not-started",
            "verification": "true",
            "evidence": "",
        },
    ],
}


def setup_demo_policy():
    """Write demo-specific policy files."""
    DENY_LIST_PATH.write_text(json.dumps(DEMO_DENY_LIST, indent=2))
    ALLOWLIST_PATH.write_text(json.dumps(DEMO_ALLOWLIST, indent=2))
    FEATURE_LIST_PATH.write_text(json.dumps(DEMO_FEATURE_LIST_INITIAL, indent=2))
    # Clear audit log
    AUDIT_LOG_PATH.unlink(missing_ok=True)
    # Clean sandbox
    if WORKDIR.exists():
        import shutil
        shutil.rmtree(WORKDIR)
    WORKDIR.mkdir(exist_ok=True)


def transition_phase():
    """Simulate phase-01 transitioning to 'passing' (human sign-off)."""
    data = json.loads(FEATURE_LIST_PATH.read_text())
    for f in data["features"]:
        if f["id"] == "phase-01":
            f["status"] = "passing"
        elif f["id"] == "phase-02":
            f["status"] = "active"
    FEATURE_LIST_PATH.write_text(json.dumps(data, indent=2))


# --- Scripted model responses ---

DEMO_SCRIPT = [
    # Turn 1: Allowed tool call — bash echo (in allowlist, no deny match)
    Response(
        content=[Block(type="tool_use", name="bash",
                       input={"command": "echo 'recon scan complete'"},
                       id="call_01")],
        stop_reason="tool_use",
    ),
    # Turn 2: Phase-gated tool — exploit_runner (gated until phase-01 passing)
    Response(
        content=[Block(type="tool_use", name="exploit_runner",
                       input={"command": "run exploit/target"},
                       id="call_02")],
        stop_reason="tool_use",
    ),
    # Turn 3: After phase transition — re-request exploit_runner
    Response(
        content=[Block(type="tool_use", name="exploit_runner",
                       input={"command": "run exploit/target"},
                       id="call_03")],
        stop_reason="tool_use",
    ),
    # Turn 4: Final allowed call
    Response(
        content=[Block(type="tool_use", name="bash",
                       input={"command": "echo 'exploit complete, reporting'"},
                       id="call_04")],
        stop_reason="tool_use",
    ),
    # Turn 5: Done
    Response(
        content=[Block(type="text", text="All phases complete. Engagement done.")],
        stop_reason="end_turn",
    ),
]


def demo_with_gate():
    """Run the demo with the Permission Gate active."""
    from governance.permission import make_permission_check

    model = FakeModel(DEMO_SCRIPT)
    gate = make_permission_check()
    turn = [0]

    # Custom model wrapper that does the phase transition between turns 2 and 3
    original_call = model.__call__

    def model_with_transition(messages):
        turn[0] += 1
        if turn[0] == 3:
            # Before turn 3, simulate phase transition (after turn 2 was denied)
            print(f"\n   \033[33m↻ Phase transition\033[0m: phase-01 → passing (human sign-off)")
            print(f"   \033[33m↻ Phase transition\033[0m: phase-02 → active\n")
            transition_phase()
        resp = original_call(messages)
        return resp

    print("\n\033[1m━━━ Demo: WITH Permission Gate ━━━\033[0m\n")
    agent_loop([], model_with_transition, permission_check=gate, max_turns=10)


def demo_without_gate():
    """Run the same model WITHOUT the Permission Gate."""
    model = FakeModel(DEMO_SCRIPT)

    # Add exploit_runner handler for ungated mode
    TOOL_HANDLERS["exploit_runner"] = lambda args: f"[exploit] executed: {args.get('command', '')}"

    print("\n\033[1m━━━ Demo: WITHOUT Permission Gate (--nogate) ━━━\033[0m")
    print("\033[33m   ⚠ All calls execute regardless of policy ⚠\033[0m\n")
    agent_loop([], model, permission_check=None, max_turns=10)


def main():
    nogate = "--nogate" in sys.argv

    # Save originals so we can restore after demo
    originals = {}
    for path in [DENY_LIST_PATH, ALLOWLIST_PATH, FEATURE_LIST_PATH]:
        if path.exists():
            originals[path] = path.read_text()

    setup_demo_policy()

    # Register exploit_runner handler (returns simulated output)
    TOOL_HANDLERS["exploit_runner"] = lambda args: f"[exploit] executed: {args.get('command', '')}"

    try:
        if nogate:
            demo_without_gate()
        else:
            demo_with_gate()
    finally:
        # Restore original policy files
        for path, content in originals.items():
            path.write_text(content)

    print("\n\033[1m━━━ Demo Complete ━━━\033[0m")
    if not nogate:
        print("Re-run with --nogate to see the same model with zero enforcement.")


if __name__ == "__main__":
    main()
