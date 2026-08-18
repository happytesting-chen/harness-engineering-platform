"""
Secret-block hook adapter — Gate for credential leakage in writes.

Reads a Claude Code PreToolUse envelope on stdin, decodes the tool input, and
scans the *decoded* text (file content, command, etc.) for hardcoded credentials.

Blocks by exiting 2 (the only exit code Claude Code treats as a block). Fails
CLOSED: malformed or empty input is blocked, never allowed by accident.

Why a script and not an inline one-liner: the previous inline hook regex ran
against the raw escaped JSON on stdin, where a quote after `=` arrives as `\"`,
so `api_key="..."` slipped through. Decoding tool_input first fixes that.
"""
import json
import re
import sys

# Credential patterns. Matched against decoded strings (quotes are real quotes).
_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password|passwd|pwd)\s*[=:]\s*[\"'][^\"']+[\"']"),
    re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*\S+"),
    # Hyphens and underscores are INSIDE the class: without them this stopped at
    # "sk-ant" (6 chars, under the floor) and missed every current Anthropic key.
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]

_BEFORE_KEYS = frozenset({"old_string", "old_str"})
_MAX_DEPTH = 12


def _walk_strings(node, out: list, depth: int = 0) -> None:
    if depth > _MAX_DEPTH:
        return
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for key, val in node.items():
            if key in _BEFORE_KEYS:
                continue
            _walk_strings(val, out, depth + 1)
    elif isinstance(node, (list, tuple)):
        for val in node:
            _walk_strings(val, out, depth + 1)


def _collect_text(tool_input) -> str:
    parts: list = []
    _walk_strings(tool_input, parts)
    return "\n".join(parts)


def _block(reason: str):
    print(reason, file=sys.stderr)
    sys.exit(2)


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        _block("secret-block: empty stdin (fail closed)")
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        _block("secret-block: malformed hook payload (fail closed)")
    if not isinstance(data, dict):
        _block("secret-block: unexpected hook payload shape (fail closed)")

    text = _collect_text(data.get("tool_input", {}))
    for pat in _PATTERNS:
        if pat.search(text):
            _block("secret-block: possible hardcoded credential in tool input")
    sys.exit(0)


if __name__ == "__main__":
    main()
