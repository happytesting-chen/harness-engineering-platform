"""
Runtime screen — positions ① and ④ for a DEPLOYED application.

`prompt_screen.py` and `result_screen.py` hold the same two positions, but they are
*hook adapters*: they read a Claude Code envelope on stdin and speak in exit codes.
Hooks are an IDE-agent feature. A shipped application has no hook runtime, so it
inherits the design of the harness and none of its enforcement. This module is the
in-process half — the same two gates, as plain functions an application calls.

    ①  screen_input(text)          before the model reads an external request
    ④  screen_result(result, tool)  before the model reads a tool's output

Both defer to `content_trust.py`, which stays the single owner of the marker list, and
④ additionally defers to `result_screen.screen` for the substitution itself. So this
file contains no patterns of its own and no notice text of its own: tuning detection in
one place still moves every position at once. `tests/test_runtime_screen.py` asserts that
this file compiles no pattern of its own — the same anti-drift check the two hook
adapters carry, which is also why the forbidden token is not spelled out here.

Four decisions worth arguing with:

1.  ① MATTERS MORE HERE THAN IT DOES IN CLAUDE CODE, which is the opposite of how it
    reads. `prompt_screen.py`'s own docstring says `UserPromptSubmit` "fires once per
    HUMAN turn and never for a subagent, so this screen contributes nothing during a
    run." In a deployed application every turn is an external turn: the request is the
    untrusted input, and there is no operator watching it arrive. Measured on
    dev_fengmin 2026-08-21, `examples/ai-news/src/app.py:133-134` was
    `def _run_agent(prompt): return _get_agent()(prompt)` — an agent behind an HTTP
    boundary with position ① entirely absent.

2.  ① FAILS CLOSED, and here it diverges from `prompt_screen.py` on purpose. That file
    fails *open* because a hook envelope whose shape drifts would otherwise erase every
    prompt and lock the operator out of their own agent with no way to say so. In
    process there is no envelope: the caller hands over a `str` or it does not, and the
    party inconvenienced by a refusal is an external requester rather than the operator.
    The availability argument does not carry over, so a value that cannot be scanned is
    rejected rather than waved through. Note that `content_trust.scan_text` returns `[]`
    for a non-`str`, so this has to be an explicit check — inheriting the library's
    tolerance would make "unscannable" indistinguishable from "clean".

3.  ④ SUBSTITUTES; IT DOES NOT RAISE. Position ② can refuse, because the side effect has
    not happened yet. By ④ the tool has already run: there is nothing left to prevent,
    and the only question is what enters the context window. Raising also breaks the
    agent loop, which then has to be repaired by the application — and the obvious
    repair is to hand the exception text back to the model, i.e. to reintroduce a
    payload one indirection later. Returning `result_screen`'s shape-preserving notice
    keeps the loop running and tells the model, in our words only, that the output was
    withheld. This matches `demo/harness.py` and the `PostToolUse` hook, so all three
    ④ implementations now agree. (dev_fengmin's `_screen_result` raised
    `PermissionError`; that is the outlier, and its own `agent.py` fed the reason string
    straight back into the model's context.)

4.  THERE IS NO WARN MODE. The hook adapters carry `PROMPT_SCREEN_MODE` /
    `RESULT_SCREEN_MODE` because a repo that *discusses* injection trips its own markers
    and a developer needs an escape hatch. A deployed application's traffic is not that
    repo, and an escape hatch on a production data-plane control is a liability with a
    predictable failure mode: it gets set during an incident and never unset. An
    operator who genuinely needs one should add it here, as an env var read in
    `screen_input` — never as an in-band phrase, which would be a bypass an attacker can
    paste into the request being screened.

Residual gap, stated rather than papered over: nothing mechanically forces an
application to call ①. Gate ② is unavoidable because tool calls route through
`RuntimeDispatcher`, and ④ is on by default inside it, but ① sits at the request
boundary, which only the application owns. See SECURITY.md S1.6 for the wiring.
"""
import sys
from pathlib import Path

# content_trust.py owns the marker list; result_screen.py owns the ④ notice and the
# shape-preserving substitution. Importing both is what keeps this file free of any
# second copy that could drift from them.
sys.path.insert(0, str(Path(__file__).parent))
from content_trust import scan_text            # noqa: E402
from result_screen import screen as _screen_response  # noqa: E402

PROJECT_ROOT = Path(__file__).parent.parent

_MAX_MARKERS_SHOWN = 4


class InputRejected(Exception):
    """Position ① refused an external request.

    Deliberately not `PermissionError`. A permission error means "this action is not
    allowed", which is gate ②'s verdict about the control plane. This is a statement
    about *content*, and an application usually wants to render the two differently —
    a 403 versus a 400. `.markers` carries our own pattern sources, never the
    rejected text.
    """

    def __init__(self, message: str, markers: list):
        super().__init__(message)
        self.markers = list(markers)


def _audit(event: str, subject: str, markers: list, decision: str, reason: str) -> None:
    """Best-effort audit line. Never allowed to change the verdict.

    Mirrors the denial-audit blocks in `permission.py` and the two hook adapters: the
    record is evidence, not part of the decision, so an unwritable log must not turn a
    rejection into a pass-through.
    """
    try:
        sys.path.insert(
            0, str(PROJECT_ROOT / "Harness-Best-Practice" / "observability"))
        from audit import record
        record(event, subject, {"markers": markers}, decision, reason)
    except Exception:
        pass


def _marker_summary(markers: list) -> str:
    shown = ", ".join(markers[:_MAX_MARKERS_SHOWN])
    if len(markers) <= _MAX_MARKERS_SHOWN:
        return shown
    return f"{shown} (+{len(markers) - _MAX_MARKERS_SHOWN} more)"


def screen_input(text, *, source: str = "request") -> str:
    """Gate ①. Return `text` unchanged if it is clean; raise `InputRejected` if not.

    Returning the value means both call shapes are safe, which is the point:

        prompt = screen_input(prompt)   # explicit
        screen_input(prompt)            # also fine — a match raises

    There is no shape that silently skips the check, because the refusal is an
    exception rather than a return value a caller can drop.

    Fails closed on anything that is not a `str` — see decision 2. `source` is a label
    for the audit line only; it is never scanned and never echoed back.
    """
    if not isinstance(text, str):
        reason = (f"runtime input screen: expected str, got "
                  f"{type(text).__name__} — cannot screen (fail closed)")
        _audit("runtime_input", source, [], "DENIED", reason)
        raise InputRejected(reason, [])

    markers = scan_text(text)
    if not markers:
        return text

    # Our own pattern sources only. Quoting the request back would put the payload into
    # whatever logs or error responses the application builds from this message.
    reason = (f"runtime input screen: request rejected — instruction-shaped text "
              f"matched {len(markers)} marker(s): {_marker_summary(markers)}")
    _audit("runtime_input", source, markers, "DENIED", reason)
    raise InputRejected(reason, markers)


def screen_result(result, tool: str = "unknown"):
    """Gate ④. Return `result`, or a shape-preserving notice replacing it.

    Delegates the decision and the substitution to `result_screen.screen`, so the
    in-process path and the `PostToolUse` hook cannot disagree about what counts as a
    match or about what the model is told. Never raises on adversarial content — see
    decision 3.
    """
    markers, replacement = _screen_response(result, tool)
    if not markers:
        return result
    _audit("runtime_result", tool, markers, "WITHHELD",
           "instruction-shaped text in tool output")
    return replacement
