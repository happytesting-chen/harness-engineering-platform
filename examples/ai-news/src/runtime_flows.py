"""Canonical model-independent UI flows for runtime-security demonstrations.

The application selects a pre-written flow from the actual runtime audit decision.
The LLM does not decide which flow is displayed, keeping the PoC fast and stable
across model changes.
"""


def _flow(title: str, caption: str, body: str, result: str) -> dict:
    return {"title": title, "caption": caption, "flow": body, "result": result}


RUNTIME_FLOWS = {
    ("Tool Permission", "BLOCK"): _flow(
        "Tool Permission Flow — Blocked",
        "The LLM requested delete_digest, but runtime permission denied execution.",
        "User: Delete the latest digest now.\n"
        "    ↓\n"
        "LLM reasoning\n"
        "decides delete_digest(...) is needed\n"
        "    ↓\n"
        "Tool-call request created\n"
        "    ↓\n"
        "┌──────────────────────────────────┐\n"
        "│       TOOL PERMISSION POLICY     │\n"
        "│  Is delete_digest authorized?    │\n"
        "└──────────────────────────────────┘\n"
        "    ↓\n"
        "Real delete handler never executes\n"
        "    ↓\n"
        "LLM receives runtime block result\n"
        "    ↓\n"
        "LLM summarizes the block reason to user",
        "NOT APPROVED → BLOCKED",
    ),
    ("Tool Permission", "ALLOW"): _flow(
        "Tool Permission Flow — Allowed",
        "Runtime permission confirmed that the requested tool is authorized.",
        "User Input\n    ↓\nLLM reasoning\nchooses an approved tool\n    ↓\nTool-call request created\n    ↓\nTOOL PERMISSION POLICY\n    ↓\nReal tool handler executes\n    ↓\nResult returns to LLM\n    ↓\nLLM answers user",
        "APPROVED → ALLOWED",
    ),
    ("Allowed Egress", "ALLOW"): _flow(
        "Egress Control Flow — Allowed",
        "Runtime egress policy confirmed that the requested destination is approved.",
        "User Input\n"
        "    ↓\n"
        "LLM reasoning\n"
        "decides external data is needed\n"
        "    ↓\n"
        "get_trending_repos(endpoint=api.github.com, ...) requested\n"
        "    ↓\n"
        "┌──────────────────────────────────┐\n"
        "│          EGRESS CONTROL          │\n"
        "│  Is destination host approved?   │\n"
        "└──────────────────────────────────┘\n"
        "    ↓\n"
        "Real network request executes\n"
        "    ↓\n"
        "Tool result returns to LLM\n"
        "    ↓\n"
        "LLM summarizes result to user",
        "api.github.com APPROVED → ALLOWED",
    ),
    ("Allowed Egress", "BLOCK"): _flow(
        "Egress Control Flow — Blocked",
        "The requested destination did not pass runtime egress policy.",
        "User Input\n    ↓\nLLM reasoning\nrequests network tool\n    ↓\nEGRESS CONTROL\n    ↓\nReal network request never executes\n    ↓\nLLM receives block result\n    ↓\nLLM summarizes reason",
        "DESTINATION NOT APPROVED → BLOCKED",
    ),
    ("Blocked Egress", "BLOCK"): _flow(
        "Egress Control Flow — Blocked",
        "A legitimate destination is still denied because it is outside the application's approved egress policy.",
        "User Input\n"
        "    ↓\n"
        "LLM reasoning\n"
        "decides fetch_news is needed\n"
        "    ↓\n"
        "fetch_news(url=arstechnica.com/...) requested\n"
        "    ↓\n"
        "┌──────────────────────────────────┐\n"
        "│          EGRESS CONTROL          │\n"
        "│  Is destination host approved?   │\n"
        "└──────────────────────────────────┘\n"
        "    ↓\n"
        "Real network request never executes\n"
        "    ↓\n"
        "LLM receives runtime block result\n"
        "    ↓\n"
        "LLM summarizes block reason to user",
        "arstechnica.com NOT APPROVED → BLOCKED",
    ),
    ("Blocked Egress", "ALLOW"): _flow(
        "Egress Control Flow — Allowed",
        "The actual runtime decision allowed the destination.",
        "User Input\n    ↓\nLLM reasoning\nrequests network tool\n    ↓\nEGRESS CONTROL\n    ↓\nReal network request executes\n    ↓\nResult returns to LLM\n    ↓\nLLM answers user",
        "DESTINATION APPROVED → ALLOWED",
    ),
    ("Secret Protection", "BLOCK"): _flow(
        "Secret Protection Flow — Blocked",
        "Secret Protection detected protected or credential-like data in the proposed tool arguments and stopped execution.",
        "User Input\n"
        "    ↓\n"
        "LLM obtains controlled synthetic credential\n"
        "    ↓\n"
        "LLM reasoning\n"
        "decides to call save_digest(...)\n"
        "    ↓\n"
        "Tool name + arguments generated\n"
        "    ↓\n"
        "┌──────────────────────────────────┐\n"
        "│       SECRET PROTECTION          │\n"
        "│ Scan tool-call arguments before  │\n"
        "│ actual tool execution            │\n"
        "└──────────────────────────────────┘\n"
        "    ↓\n"
        "save_digest handler never executes\n"
        "    ↓\n"
        "LLM receives block result\n"
        "    ↓\n"
        "LLM summarizes block reason to user",
        "PROTECTED SECRET DETECTED → BLOCKED",
    ),
    ("Secret Protection", "ALLOW"): _flow(
        "Secret Protection Flow — Allowed",
        "No protected or credential-like data was detected in the proposed tool arguments.",
        "User Input\n    ↓\nLLM reasoning\nproposes tool call\n    ↓\nTool name + arguments generated\n    ↓\nSECRET PROTECTION scans arguments\n    ↓\nTool proceeds to remaining runtime checks / execution",
        "NO PROTECTED SECRET DETECTED → ALLOWED",
    ),
    ("Content Trust", "BLOCK"): _flow(
        "Content Trust Flow — Blocked",
        "The fetched external content contained instruction-shaped content, so Content Trust blocked it before normal model use.",
        "User Input\n"
        "    ↓\n"
        "LLM reasoning\n"
        "decides fetch_news is needed\n"
        "    ↓\n"
        "fetch_news(...) passes permission / egress checks\n"
        "    ↓\n"
        "Real fetch_news tool executes\n"
        "    ↓\n"
        "External article content returned\n"
        "    ↓\n"
        "┌──────────────────────────────────┐\n"
        "│          CONTENT TRUST           │\n"
        "│ Scan untrusted tool output before│\n"
        "│ normal model-context use         │\n"
        "└──────────────────────────────────┘\n"
        "    ↓\n"
        "Suspicious content is NOT exposed for normal LLM use\n"
        "    ↓\n"
        "LLM receives structured block result\n"
        "    ↓\n"
        "LLM summarizes block reason to user",
        "SUSPICIOUS CONTENT DETECTED → BLOCKED",
    ),
    ("Content Trust", "ALLOW"): _flow(
        "Content Trust Flow — Allowed",
        "The fetched external content passed Content Trust and can be returned to the LLM for normal use.",
        "User Input\n"
        "    ↓\n"
        "LLM reasoning\n"
        "decides fetch_news is needed\n"
        "    ↓\n"
        "fetch_news(...) passes permission / egress checks\n"
        "    ↓\n"
        "Real fetch_news tool executes\n"
        "    ↓\n"
        "External article content returned\n"
        "    ↓\n"
        "┌──────────────────────────────────┐\n"
        "│          CONTENT TRUST           │\n"
        "│ Scan untrusted tool output before│\n"
        "│ normal model-context use         │\n"
        "└──────────────────────────────────┘\n"
        "    ↓\n"
        "Content returned to LLM for normal use\n"
        "    ↓\n"
        "LLM uses content to answer user",
        "NO SUSPICIOUS CONTENT DETECTED → ALLOWED",
    ),
}


def get_runtime_flow(scenario: str, decision: str | None = None) -> dict | None:
    """Return the flow matching the actual runtime decision for this scenario."""
    normalized = (decision or "").upper()
    if normalized in {"DENY", "DENIED", "BLOCKED"}:
        normalized = "BLOCK"
    elif normalized in {"ALLOWED", "APPROVED", "PASS", "PASSED"}:
        normalized = "ALLOW"
    return RUNTIME_FLOWS.get((scenario, normalized))
