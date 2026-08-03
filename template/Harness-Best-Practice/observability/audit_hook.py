"""
Audit-capture hook adapter — PostToolUse accountability record.

Reads a Claude Code PostToolUse envelope on stdin and appends one audit-log line
recording the REAL tool name. The previous inline hook wrote the literal string
"$TOOL_NAME" (single-quoted, never expanded) or an empty string (double-quoted,
unset env var) because Claude Code passes the payload on stdin, not as env vars.

Never blocks: audit is observability, not enforcement. Always exits 0, even on
malformed input (a broken logger must not wedge the tool pipeline).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from audit import record  # noqa: E402


def main():
    raw = sys.stdin.read().strip()
    tool_name = "unknown"
    decision = "INFO"
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                tool_name = data.get("tool_name", "unknown") or "unknown"
                resp = data.get("tool_response", {})
                if isinstance(resp, dict) and resp.get("error"):
                    decision = "ERROR"
                else:
                    decision = "ALLOWED"
        except (json.JSONDecodeError, ValueError):
            pass
    record("tool_complete", tool_name, {}, decision)
    sys.exit(0)


if __name__ == "__main__":
    main()
