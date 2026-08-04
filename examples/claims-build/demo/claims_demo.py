#!/usr/bin/env python3
"""Claims demo — the gate governs the REAL claims tool (claims_runner).

Unlike demo.py (a generic pentest illustration), this exercises the actual
project tool named in governance/mcp-allowlist.json:

  Turn 1: bash echo (ungated)                        → ✓ execute
  Turn 2: claims_runner while phase-01 is active-but-not-passing → ⛔ DENIED
  Turn 3: human sign-off — phase-01 → passing
  Turn 4: claims_runner again                         → ✓ now runs the real
          claims.runner on a committed SYN-* fixture and writes one minimal result
  Turn 5: done

The claims_runner handler calls claims.runner.run — so an ALLOW here is a real
decision + fail-closed write, not a simulated string. No API key, no network.

    python3 demo/claims_demo.py            # with the gate
    python3 demo/claims_demo.py --nogate   # same model, no enforcement
"""
import json
import shutil
import sys
from pathlib import Path

DEMO_DIR = Path(__file__).parent
TEMPLATE_ROOT = DEMO_DIR.parent
sys.path.insert(0, str(TEMPLATE_ROOT))
sys.path.insert(0, str(DEMO_DIR))
sys.path.insert(0, str(TEMPLATE_ROOT / "governance"))
sys.path.insert(0, str(TEMPLATE_ROOT / "Harness-Best-Practice" / "observability"))
sys.path.insert(0, str(TEMPLATE_ROOT / "Harness-Best-Practice"))

from fake_model import Block, Response, FakeModel
from harness import agent_loop, TOOL_HANDLERS, WORKDIR
from observability.audit import LOG as AUDIT_LOG_PATH

from claims.runner import run as claims_run

DENY_LIST_PATH = TEMPLATE_ROOT / "governance" / "deny-list.json"
ALLOWLIST_PATH = TEMPLATE_ROOT / "governance" / "mcp-allowlist.json"
FEATURE_LIST_PATH = TEMPLATE_ROOT / "Harness-Best-Practice" / "feature_list.json"

# A committed synthetic fixture the demo feeds to the real runner.
DEMO_FIXTURE = TEMPLATE_ROOT / "claims" / "tests" / "fixtures" / "SYN-FIXTURE-001-approved.json"
RESULT_DIR = WORKDIR / "claims_results"

DEMO_DENY_LIST = {"patterns": ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "> /dev/"]}

# Mirrors the project's real allowlist: claims_runner gated_until phase-01.
DEMO_ALLOWLIST = {
    "tools": [
        {"name": "bash", "description": "Shell commands", "version": "1.0"},
        {"name": "write_file", "description": "Write files", "version": "1.0"},
        {"name": "claims_runner", "description": "Deterministic claims entrypoint",
         "version": "1.0", "gated_until": "phase-01"},
    ],
    "egress_hosts": [],
}

DEMO_FEATURE_LIST_INITIAL = {
    "project": "claims-demo",
    "description": "Phase-gated enforcement over the real claims tool",
    "features": [
        {"id": "phase-01", "name": "Build A readiness review", "dependencies": [],
         "status": "active", "verification": "true", "evidence": ""},
        {"id": "phase-02", "name": "Deterministic Build A implementation",
         "dependencies": ["phase-01"], "status": "not-started",
         "verification": "true", "evidence": ""},
    ],
}


def _claims_runner_handler(args: dict) -> str:
    """Invoke the REAL claims entrypoint; report its outcome + exit code."""
    fixture = Path(args.get("fixture", DEMO_FIXTURE))
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    code = claims_run(fixture, out_dir=RESULT_DIR)
    return f"[claims_runner] exit={code}; result written under {RESULT_DIR.name}/"


def setup_demo_policy():
    DENY_LIST_PATH.write_text(json.dumps(DEMO_DENY_LIST, indent=2))
    ALLOWLIST_PATH.write_text(json.dumps(DEMO_ALLOWLIST, indent=2))
    FEATURE_LIST_PATH.write_text(json.dumps(DEMO_FEATURE_LIST_INITIAL, indent=2))
    AUDIT_LOG_PATH.unlink(missing_ok=True)
    if WORKDIR.exists():
        shutil.rmtree(WORKDIR)
    WORKDIR.mkdir(exist_ok=True)


def transition_phase():
    data = json.loads(FEATURE_LIST_PATH.read_text())
    for f in data["features"]:
        if f["id"] == "phase-01":
            f["status"] = "passing"
        elif f["id"] == "phase-02":
            f["status"] = "active"
    FEATURE_LIST_PATH.write_text(json.dumps(data, indent=2))


DEMO_SCRIPT = [
    Response(content=[Block(type="tool_use", name="bash",
                            input={"command": "echo 'intake received'"}, id="c1")],
             stop_reason="tool_use"),
    Response(content=[Block(type="tool_use", name="claims_runner",
                            input={"fixture": str(DEMO_FIXTURE)}, id="c2")],
             stop_reason="tool_use"),
    Response(content=[Block(type="tool_use", name="claims_runner",
                            input={"fixture": str(DEMO_FIXTURE)}, id="c3")],
             stop_reason="tool_use"),
    Response(content=[Block(type="text", text="Claim processed under enforcement. Done.")],
             stop_reason="end_turn"),
]


def demo_with_gate():
    from governance.permission import make_permission_check

    model = FakeModel(DEMO_SCRIPT)
    gate = make_permission_check()
    turn = [0]
    original_call = model.__call__

    def model_with_transition(messages):
        turn[0] += 1
        if turn[0] == 3:
            print("\n   \033[33m↻ Phase transition\033[0m: phase-01 → passing (human sign-off)")
            print("   \033[33m↻ Phase transition\033[0m: phase-02 → active\n")
            transition_phase()
        return original_call(messages)

    print("\n\033[1m━━━ Claims Demo: WITH Permission Gate ━━━\033[0m\n")
    agent_loop([], model_with_transition, permission_check=gate, max_turns=10)


def demo_without_gate():
    model = FakeModel(DEMO_SCRIPT)
    print("\n\033[1m━━━ Claims Demo: WITHOUT Permission Gate (--nogate) ━━━\033[0m")
    print("\033[33m   ⚠ claims_runner executes even while phase-01 is unsigned ⚠\033[0m\n")
    agent_loop([], model, permission_check=None, max_turns=10)


def main():
    nogate = "--nogate" in sys.argv
    originals = {p: p.read_text() for p in
                 [DENY_LIST_PATH, ALLOWLIST_PATH, FEATURE_LIST_PATH] if p.exists()}
    setup_demo_policy()
    TOOL_HANDLERS["claims_runner"] = _claims_runner_handler
    try:
        demo_without_gate() if nogate else demo_with_gate()
    finally:
        for path, content in originals.items():
            path.write_text(content)

    print("\n\033[1m━━━ Claims Demo Complete ━━━\033[0m")
    if not nogate:
        print("Re-run with --nogate to see claims_runner execute with zero enforcement.")


if __name__ == "__main__":
    main()
