"""
Prompt-screen hook adapter — Gate at position ①, before the model sees the turn.

Reads a Claude Code `UserPromptSubmit` envelope on stdin and scans it for
instruction-shaped text using the marker list in `content_trust.py`. On a match it
exits 2, which per the hooks docs "blocks prompt processing and erases the prompt".
Nothing reaches the model.

This is one of two places where injection is stopped before the LLM. The other is
position ④, held by the shared `result_screen.py` on `PostToolUse`.
"""
import json
import os
import sys
from pathlib import Path

# Shared security owns the marker list. Build-time adapters consume it rather than
# maintaining a second copy.
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "security" / "shared"))
from content_trust import scan_text  # noqa: E402

_METADATA_KEYS = frozenset({
    "session_id", "prompt_id", "transcript_path", "cwd",
    "permission_mode", "hook_event_name",
})
_MAX_DEPTH = 12
_MAX_MARKERS_SHOWN = 4


def _walk_strings(node, out: list, depth: int = 0) -> None:
    if depth > _MAX_DEPTH:
        return
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for key, val in node.items():
            if key in _METADATA_KEYS:
                continue
            _walk_strings(val, out, depth + 1)
    elif isinstance(node, (list, tuple)):
        for val in node:
            _walk_strings(val, out, depth + 1)


def collect_text(envelope) -> str:
    parts: list = []
    _walk_strings(envelope, parts)
    return "\n".join(parts)


def _audit(markers: list, decision: str) -> None:
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "Harness-Best-Practice" / "observability"))
        from audit import record
        record("UserPromptSubmit", "prompt", {"markers": markers}, decision,
               "instruction-shaped text in prompt")
    except Exception:
        pass


def _block(markers: list):
    shown = ", ".join(markers[:_MAX_MARKERS_SHOWN])
    extra = "" if len(markers) <= _MAX_MARKERS_SHOWN else \
        f" (+{len(markers) - _MAX_MARKERS_SHOWN} more)"
    print(f"prompt-screen: prompt erased -- instruction-shaped text matched "
          f"{len(markers)} marker(s): {shown}{extra}. "
          f"Set PROMPT_SCREEN_MODE=warn to allow prompts like this through.",
          file=sys.stderr)
    _audit(markers, "DENIED")
    sys.exit(2)


def _warn(markers: list):
    print(f"prompt-screen: {len(markers)} marker(s) matched, allowed "
          f"(PROMPT_SCREEN_MODE=warn)", file=sys.stderr)
    _audit(markers, "ALLOWED")
    sys.exit(0)


def _fail_open(note: str):
    print(f"prompt-screen: {note} -- not screened (fail open)", file=sys.stderr)
    sys.exit(0)


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        _fail_open("empty stdin")
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        _fail_open("malformed hook payload")
    if not isinstance(data, dict):
        _fail_open("unexpected hook payload shape")

    markers = scan_text(collect_text(data))
    if markers:
        if os.environ.get("PROMPT_SCREEN_MODE", "block").strip().lower() == "warn":
            _warn(markers)
        _block(markers)
    sys.exit(0)


if __name__ == "__main__":
    main()
