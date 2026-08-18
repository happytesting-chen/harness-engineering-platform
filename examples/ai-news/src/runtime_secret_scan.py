# ** newly added **
"""Runtime secret scanner for deployed AI News tool calls.

This file is intentionally separate from `Security-kit/secret_scan.py`, which remains
Claude Code's build-time PreToolUse hook adapter. The runtime agent calls this module
directly before any outbound/write-capable tool handler executes.
"""

import re

_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|pwd)\s*[=:]\s*[\"'][^\"']+[\"']"),
    re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*\S+"),
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]

_MAX_DEPTH = 12


def _walk_strings(node, out: list[str], depth: int = 0) -> None:
    """Collect every string reachable in runtime tool input."""
    if depth > _MAX_DEPTH:
        return
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for value in node.values():
            _walk_strings(value, out, depth + 1)
    elif isinstance(node, (list, tuple)):
        for value in node:
            _walk_strings(value, out, depth + 1)


def scan_tool_input(tool_input) -> str | None:
    """Return a blocking reason when runtime tool input contains a secret pattern.

    Returns None when no configured credential pattern is detected. The caller must
    perform this check before executing the real tool handler.
    """
    parts: list[str] = []
    _walk_strings(tool_input, parts)
    text = "\n".join(parts)

    for pattern in _PATTERNS:
        if pattern.search(text):
            return "secret-block: possible credential in runtime tool input"
    return None
# ** newly added **
