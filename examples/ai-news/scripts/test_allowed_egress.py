# ** newly added **
"""Live test: approved egress is allowed through the real Claude/Strands path."""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import build_agent

AUDIT_LOG = PROJECT_ROOT / "Harness-Best-Practice" / "observability" / "audit.log"


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set. Export it locally before running.")

    offset = AUDIT_LOG.stat().st_size if AUDIT_LOG.exists() else 0
    agent = build_agent()
    result = agent(
        "You must call the get_trending_repos tool with days=7. "
        "Use the returned data to briefly report the top repositories."
    )
    print("\nAgent result:\n", result)
    print("\nRuntime audit events:")

    if not AUDIT_LOG.exists():
        print("(no new runtime audit events)")
        return

    with AUDIT_LOG.open("r", encoding="utf-8") as handle:
        handle.seek(offset)
        found = False
        for line in handle:
            line = line.strip()
            if line:
                found = True
                try:
                    print(json.dumps(json.loads(line), indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    print(line)
        if not found:
            print("(no new runtime audit events)")


if __name__ == "__main__":
    main()
# ** newly added **
