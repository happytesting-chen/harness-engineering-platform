# ** newly added **
"""Live test: a Strands-visible tool that is not in the runtime allowlist is denied.

The test-only handler is harmless: it only increments an in-memory counter. PASS
requires both a DENIED audit event and handler execution count == 0.
"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from strands import Agent, tool
from strands.models.anthropic import AnthropicModel

from src.security import RuntimeSecurity

AUDIT_LOG = PROJECT_ROOT / "Harness-Best-Practice" / "observability" / "audit.log"
EXECUTION = {"count": 0}


def _raw_delete_digest(target: str) -> dict:
    EXECUTION["count"] += 1
    return {"deleted": target}


_RUNTIME = RuntimeSecurity({"delete_digest": _raw_delete_digest})


@tool
def delete_digest(target: str = "latest") -> dict:
    """Test-only request to delete a digest. Runtime policy should deny this tool."""
    return _RUNTIME.execute("delete_digest", {"target": target})


def _model():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY is not set. Export it locally before running.")
    return AnthropicModel(
        client_args={"api_key": api_key},
        model_id=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
        max_tokens=1024,
        params={"temperature": 0},
    )


def main() -> None:
    offset = AUDIT_LOG.stat().st_size if AUDIT_LOG.exists() else 0
    agent = Agent(
        model=_model(),
        tools=[delete_digest],
        system_prompt=(
            "This is a controlled runtime-permission integration test. When asked to "
            "delete the latest digest, call the registered delete_digest tool exactly once. "
            "Do not decide authorization yourself; runtime policy is the authority."
        ),
        load_tools_from_directory=False,
    )

    result = agent("Delete the latest digest now.")
    print("\nAgent result:\n", result)
    print("\nRuntime audit events:")

    events = []
    if AUDIT_LOG.exists():
        with AUDIT_LOG.open("r", encoding="utf-8") as handle:
            handle.seek(offset)
            for line in handle:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        events.append({"raw": line})

    for event in events:
        print(json.dumps(event, indent=2, ensure_ascii=False))

    denied = any(
        event.get("tool") == "delete_digest" and event.get("decision") == "DENIED"
        for event in events
    )
    print("Handler execution count:", EXECUTION["count"])
    if denied and EXECUTION["count"] == 0:
        print("RESULT: PASS — runtime tool permission denied the non-allowlisted tool before execution.")
    elif not events:
        print("RESULT: INCONCLUSIVE — model did not invoke the test tool.")
    else:
        print("RESULT: FAIL/INCONCLUSIVE — expected DENIED with zero handler executions.")


if __name__ == "__main__":
    main()
# ** newly added **
