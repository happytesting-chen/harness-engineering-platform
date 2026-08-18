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
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),        # OpenAI- and Anthropic-style keys
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),         # GitHub personal access tokens
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


# Keys whose value is the text being REPLACED, not written. Skipped so that
# deleting a hardcoded credential from a file is not itself blocked.
_BEFORE_KEYS = frozenset({"old_string", "old_str"})
_MAX_DEPTH = 12


def _walk_strings(node, out: list, depth: int = 0) -> None:
    """Collect every string reachable in a decoded tool_input."""
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
    """Pull every scannable string out of a decoded tool_input.

    Walks the whole structure rather than naming fields. The named-field version
    read only top-level content/command/new_string/new_str, so a credential
    nested one level down was invisible: MultiEdit puts its payload in
    edits[].new_string and NotebookEdit in new_source, and both were ALLOWED
    with the same secret that Write and Edit blocked. The hook was registered
    for those tools and ran -- it simply could not see its input, which reads
    like coverage in .claude/settings.json while providing none.

    Walking by default is the fail-closed choice: a tool field added upstream
    is scanned without anyone remembering to add it here.
    """
    parts: list = []
    _walk_strings(tool_input, parts)
    return "\n".join(parts)


# ** newly add **
def scan_tool_input(tool_input) -> str | None:
    """Runtime-friendly secret scan over a decoded tool input.

    Returns a denial reason when a credential pattern is detected, otherwise None.
    This exposes the existing detector to deployed applications without changing the
    Claude Code hook behavior below.
    """
    text = _collect_text(tool_input)
    for pat in _PATTERNS:
        if pat.search(text):
            return "secret-block: possible hardcoded credential in tool input"
    return None
# ** newly add **


def _block(reason: str):
    # Claude Code feeds STDERR back to the model on exit 2; stdout is discarded
    # for a blocked call, so the reason must go to stderr to reach the agent.
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

    # ** newly add **
    reason = scan_tool_input(data.get("tool_input", {}))
    if reason:
        _block(reason)
    # ** newly add **
    sys.exit(0)


if __name__ == "__main__":
    main()
