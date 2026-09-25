"""Sign off a phase after verification passes.

Usage:
    python3 security/shared/signoff.py phase-01

This appends the phase ID to signed_off_phases in mcp-allowlist.json.
Operation is APPEND-ONLY and IDEMPOTENT — re-signing a phase is a no-op.
The file is a protected path; only the developer (human) should run this.
"""
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ALLOWLIST = _PROJECT_ROOT / "security" / "shared" / "mcp-allowlist.json"
_AUDIT_DIR = _PROJECT_ROOT / "Harness-Best-Practice" / "observability"


def _audit(phase_id: str, signed_off: list) -> None:
    try:
        sys.path.insert(0, str(_AUDIT_DIR))
        from audit import record
        record("phase_signoff", phase_id, {"signed_off_phases": signed_off},
               "APPROVED", f"developer signed off {phase_id}")
    except Exception:
        pass


def signoff(phase_id: str) -> None:
    if not _ALLOWLIST.exists():
        sys.exit(f"ERROR: {_ALLOWLIST} not found")

    data = json.loads(_ALLOWLIST.read_text(encoding="utf-8"))
    phases = set(data.get("signed_off_phases", []))

    if phase_id in phases:
        print(f"Already signed off: {phase_id}")
        return

    phases.add(phase_id)
    data["signed_off_phases"] = sorted(phases)
    _ALLOWLIST.write_text(json.dumps(data, indent=2), encoding="utf-8")
    _audit(phase_id, sorted(phases))
    print(f"Signed off: {phase_id}")
    print(f"Active approvals: {sorted(phases)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"Usage: python3 {Path(__file__).name} <phase-id>")
    signoff(sys.argv[1])
