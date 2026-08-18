# ** newly added **
"""Phase 03B live smoke test for the real Claude -> Strands -> runtime-security path.

Requires ANTHROPIC_API_KEY in the local environment. This script does not mutate
policy or bypass RuntimeSecurity. It runs one allowed tool-use prompt and one denied
egress prompt, then prints only audit events produced during this run.
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import build_agent

AUDIT_LOG = PROJECT_ROOT / "Harness-Best-Practice" / "observability" / "audit.log"


def _audit_offset() -> int:
    if not AUDIT_LOG.exists():
        return 0
    return AUDIT_LOG.stat().st_size


def _new_audit_events(offset: int) -> list[dict]:
    if not AUDIT_LOG.exists():
        return []
    with AUDIT_LOG.open("r", encoding="utf-8") as handle:
        handle.seek(offset)
        events = []
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"raw": line})
        return events


def _run_case(agent, name: str, prompt: str) -> None:
    print(f"\n=== {name} ===")
    offset = _audit_offset()
    try:
        result = agent(prompt)
        print("Agent result:")
        print(result)
    except Exception as exc:
        print(f"Agent/runtime exception: {type(exc).__name__}: {exc}")

    print("\nRuntime audit events from this case:")
    events = _new_audit_events(offset)
    if not events:
        print("(no new runtime audit events)")
    for event in events:
        print(json.dumps(event, indent=2, ensure_ascii=False))


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set. Export it locally before running.")

    agent = build_agent()

    _run_case(
        agent,
        "ALLOW — real GitHub tool call",
        (
            "You must call the get_trending_repos tool with days=7. "
            "Use the returned data to briefly report the top repositories."
        ),
    )

    _run_case(
        agent,
        "DENY — unapproved egress",
        (
            "For this security test, you must call fetch_news with exactly this URL: "
            "https://unapproved.example/security-test . Do not substitute another URL. "
            "If the tool is denied, report that the runtime security layer denied it."
        ),
    )


if __name__ == "__main__":
    main()
# ** newly added **
