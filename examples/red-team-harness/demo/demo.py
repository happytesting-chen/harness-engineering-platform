#!/usr/bin/env python3
"""
Red Team Demo — Scripted enforcement demonstration for penetration testing.

Shows the harness enforcing scope and phase controls:
  Turn 1: nmap allowed (in allowlist, ungated, recon phase active) → ✓ execute
  Turn 2: metasploit denied (gated_until recon, recon not yet passing) → ⛔ DENIED
  Turn 3: Phase transition (recon → passing, exploit → active)
  Turn 4: metasploit now allowed → ✓ execute
  Turn 5: Agent says "done" → exit

Usage:
    python3 demo/demo.py            # With enforcement
    python3 demo/demo.py --nogate   # Same model, no enforcement
"""
import json
import sys
from pathlib import Path

# --- Path setup ---
DEMO_DIR = Path(__file__).parent
ROOT = DEMO_DIR.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(DEMO_DIR))
sys.path.insert(0, str(ROOT / "governance"))
sys.path.insert(0, str(ROOT / "observability"))

from fake_model import Block, Response, FakeModel
from harness import agent_loop, TOOL_HANDLERS, WORKDIR
import governance.permission as permission_mod
from observability.audit import LOG as AUDIT_LOG_PATH

# --- Policy paths ---
FEATURE_LIST_PATH = ROOT / "feature_list.json"


def transition_phase():
    """Simulate recon phase transitioning to 'passing' (human sign-off)."""
    data = json.loads(FEATURE_LIST_PATH.read_text())
    for f in data["features"]:
        if f["id"] == "recon":
            f["status"] = "passing"
        elif f["id"] == "exploit":
            f["status"] = "active"
    FEATURE_LIST_PATH.write_text(json.dumps(data, indent=2))


# --- Scripted model responses (pentesting-specific) ---
DEMO_SCRIPT = [
    # Turn 1: nmap scan of in-scope target (allowed — ungated tool)
    Response(
        content=[Block(type="tool_use", name="nmap",
                       input={"command": "nmap -sV 10.20.0.5"},
                       id="call_01")],
        stop_reason="tool_use",
    ),
    # Turn 2: metasploit exploit attempt (denied — gated until recon passes)
    Response(
        content=[Block(type="tool_use", name="metasploit",
                       input={"command": "use exploit/multi/handler; set RHOST 10.20.0.5; run"},
                       id="call_02")],
        stop_reason="tool_use",
    ),
    # Turn 3: metasploit retry after phase transition
    Response(
        content=[Block(type="tool_use", name="metasploit",
                       input={"command": "use exploit/multi/handler; set RHOST 10.20.0.5; run"},
                       id="call_03")],
        stop_reason="tool_use",
    ),
    # Turn 4: Final allowed call
    Response(
        content=[Block(type="tool_use", name="bash",
                       input={"command": "echo 'Exploitation complete. Generating report.'"},
                       id="call_04")],
        stop_reason="tool_use",
    ),
    # Turn 5: Done
    Response(
        content=[Block(type="text", text="Engagement complete. All findings documented.")],
        stop_reason="end_turn",
    ),
]


# --- Tool handlers for demo ---
TOOL_HANDLERS["nmap"] = lambda args: (
    f"[nmap] Scanning {args.get('command', '').split()[-1]}...\n"
    f"PORT   STATE SERVICE VERSION\n"
    f"22/tcp open  ssh     OpenSSH 8.9\n"
    f"80/tcp open  http    Apache 2.4.52\n"
    f"443/tcp open https   Apache 2.4.52"
)

TOOL_HANDLERS["metasploit"] = lambda args: (
    f"[msf] {args.get('command', '')}\n"
    f"[*] Started reverse handler\n"
    f"[+] Meterpreter session 1 opened (192.168.100.10 -> 10.20.0.5:4444)"
)


def demo_with_gate():
    """Run red team demo with Permission Gate active."""
    from governance.permission import make_permission_check

    model = FakeModel(DEMO_SCRIPT)
    gate = make_permission_check()
    turn = [0]

    original_call = model.__call__

    def model_with_transition(messages):
        turn[0] += 1
        if turn[0] == 3:
            # Before turn 3, simulate phase transition (after turn 2 was denied)
            print(f"\n   \033[33m↻ Phase transition\033[0m: recon → passing (human sign-off)")
            print(f"   \033[33m↻ Phase transition\033[0m: exploit → active\n")
            transition_phase()
        resp = original_call(messages)
        return resp

    print("\n\033[1m━━━ Red Team Demo: WITH Permission Gate ━━━\033[0m\n")
    print("  Scenario: recon phase active, metasploit gated until recon passes\n")
    agent_loop([], model_with_transition, permission_check=gate, max_turns=10)


def demo_without_gate():
    """Run same model without enforcement."""
    model = FakeModel(DEMO_SCRIPT)

    print("\n\033[1m━━━ Red Team Demo: WITHOUT Permission Gate (--nogate) ━━━\033[0m")
    print("\033[33m   ⚠ All calls execute — metasploit fires before recon! ⚠\033[0m\n")
    agent_loop([], model, permission_check=None, max_turns=10)


def main():
    nogate = "--nogate" in sys.argv

    # Clear audit log for clean demo output
    AUDIT_LOG_PATH.unlink(missing_ok=True)

    # Ensure sandbox exists
    WORKDIR.mkdir(exist_ok=True)

    # Save original feature_list to restore after demo
    original_features = FEATURE_LIST_PATH.read_text() if FEATURE_LIST_PATH.exists() else None

    # Reset feature_list to demo starting state (recon=active, exploit=not-started)
    demo_features = json.loads(original_features) if original_features else {}
    if demo_features.get("features"):
        for f in demo_features["features"]:
            if f["id"] == "recon":
                f["status"] = "active"
            elif f["id"] == "exploit":
                f["status"] = "not-started"
        FEATURE_LIST_PATH.write_text(json.dumps(demo_features, indent=2))

    try:
        if nogate:
            demo_without_gate()
        else:
            demo_with_gate()
    finally:
        # Restore original feature_list
        if original_features:
            FEATURE_LIST_PATH.write_text(original_features)

    print("\n\033[1m━━━ Demo Complete ━━━\033[0m")
    if not nogate:
        print("Re-run with --nogate to see metasploit execute before recon is verified.")
        print("\"A request is not a control\" — the harness makes the difference.")


if __name__ == "__main__":
    main()
