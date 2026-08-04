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
    re.compile(r"sk-[A-Za-z0-9]{16,}"),          # OpenAI-style keys
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),         # GitHub personal access tokens
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


def _collect_text(tool_input: dict) -> str:
    """Pull the scannable text fields out of a tool_input dict."""
    if not isinstance(tool_input, dict):
        return ""
    parts = []
    for key in ("content", "command", "new_string", "new_str"):
        val = tool_input.get(key)
        if isinstance(val, str):
            parts.append(val)
    return "\n".join(parts)


def _block(reason: str):
    print(reason)
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
