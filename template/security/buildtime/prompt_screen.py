"""
Prompt-screen hook adapter — Gate at position ①, before the model sees the turn.

Reads a Claude Code `UserPromptSubmit` envelope on stdin and scans it for
instruction-shaped text using the marker list in `content_trust.py`. On a match it
exits 2, which per the hooks docs "blocks prompt processing and erases the prompt"
(https://code.claude.com/docs/en/hooks, read 2026-08-17). Nothing reaches the model.

This is one of two places where injection is stopped *before* the LLM rather than at the
model's hands. The other is position ④ — a tool result re-entering context — held by
`result_screen.py` on `PostToolUse`, which replaces the output rather than blocking the
call. An earlier version of this docstring said ④ had no equivalent event; that was
wrong, and it kept a closable gap on the books as impossible.

The two are not interchangeable. `UserPromptSubmit` fires once per HUMAN turn and never
for a subagent, so this screen contributes nothing during a run; ④ fires per tool call
and is the pre-model control that actually covers agent runtime. Both import the same
marker list from `content_trust.py`, so tuning detection moves both at once.

Three decisions worth arguing with:

1.  It walks every string in the envelope instead of reading one field. The hooks
    docs list the common `UserPromptSubmit` keys but this adapter does not depend on
    the prompt arriving under any particular one, so a rename upstream degrades
    coverage rather than silently zeroing it. Metadata keys are skipped by name
    (`_METADATA_KEYS`) so a transcript path or cwd cannot trip a marker.

2.  It prints NOTHING to stdout on the allow path. For this event, exit-0 stdout is
    added to the model's context — a chatty "clean" line would be a new injection
    surface in the exact channel this file exists to protect.

3.  It fails OPEN on a malformed payload, unlike `secret_scan.py`, which fails
    closed. Failing closed here erases every prompt the moment the envelope shape
    changes: the user is locked out of their own agent with no way to say so, and
    the tool gates — the actual mechanical controls — are untouched either way. The
    trade is availability against a screen that was never a guarantee. A reviewer
    who disagrees should change `_fail_open` to call `_block`; nothing else moves.

Known false-positive hazard: in a repo that *discusses* injection, a prompt like
"why does `ignore all previous instructions` match?" is itself a match. Set
`PROMPT_SCREEN_MODE=warn` to report without blocking. That switch is an operator
env var on purpose — an in-band per-prompt bypass phrase would be a bypass an
attacker could paste into content.
"""
import json
import os
import sys
from pathlib import Path

# content_trust.py is the single owner of the marker list. Importing it keeps one
# definition of "instruction-shaped" across the prompt gate and the ingestion
# screen in demo/harness.py; a second copy here would drift.
sys.path.insert(0, str(Path(__file__).parent))
from content_trust import scan_text  # noqa: E402

PROJECT_ROOT = Path(__file__).parent.parent

# Envelope keys that carry plumbing, not user text. Scanning these produces pure
# false positives: a cwd or transcript path under a directory named `system:` or a
# session in a checkout called `admin-mode` is not an injection attempt.
_METADATA_KEYS = frozenset({
    "session_id", "prompt_id", "transcript_path", "cwd",
    "permission_mode", "hook_event_name",
})
_MAX_DEPTH = 12
_MAX_MARKERS_SHOWN = 4


def _walk_strings(node, out: list, depth: int = 0) -> None:
    """Collect every string reachable in the envelope, minus the metadata keys."""
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
    """Pull every scannable string out of a decoded hook envelope."""
    parts: list = []
    _walk_strings(envelope, parts)
    return "\n".join(parts)


def _audit(markers: list, decision: str) -> None:
    """Best-effort audit line. Never allowed to change the verdict.

    Mirrors the denial-audit block in governance/permission.py: the record is
    evidence, not part of the decision, so an unwritable log must not turn a block
    into an allow.
    """
    try:
        sys.path.insert(
            0, str(PROJECT_ROOT / "Harness-Best-Practice" / "observability"))
        from audit import record
        record("UserPromptSubmit", "prompt", {"markers": markers}, decision,
               "instruction-shaped text in prompt")
    except Exception:
        pass


def _block(markers: list):
    # The reason goes to stderr because that is where Claude Code reads it on a
    # block; stdout on this event would be injected into the model's context.
    # Only our own pattern sources are named -- never the matched prompt text,
    # which is the untrusted half.
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
    # See decision 3 in the module docstring. stderr, never stdout.
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
