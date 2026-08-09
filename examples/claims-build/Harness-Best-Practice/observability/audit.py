"""
Observability layer — append-only audit log.
Every tool call decision (allowed or denied) gets one JSON line.
The model cannot see or rewrite this file.
"""
import json
import time
from pathlib import Path

LOG = Path(__file__).parent / "audit.log"


def record(event: str, tool: str, detail: dict, decision: str, reason: str = ""):
    entry = {
        "timestamp": time.time(),
        "event": event,
        "tool": tool,
        "detail": detail,
        "decision": decision,
        "reason": reason,
    }
    with LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry
