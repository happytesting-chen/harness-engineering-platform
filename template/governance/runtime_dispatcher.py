"""
Runtime dispatcher — position ② for a DEPLOYED application, with ③ and ④ behind it.

Every enforcement path this template shipped before 2026-08-22 was invoked by a Claude
Code hook (`.claude/settings.json`). Hooks are an IDE-agent feature, so an application
built from the template inherited the *design* of the harness and none of its
enforcement: `permission.py` was never called, and the four gate positions collapsed to
none. This module closes that, by making a single chokepoint the only way an application
executes a tool:

    ②  the permission gate runs, and a denial raises before the tool is touched
    ③  the tool executes
    ④  its output is screened before it can re-enter the model's context

`demo/harness.py` already proved this shape — but it says so itself at the top of the
file ("This file lives in demo/ — it's optional evaluation infrastructure"), and it
carries a scripted fake model and ANSI print statements. What was missing was the same
shape as a mechanism a shipped application can import. That is all this is.

Position ① is not here, and cannot be: it sits at the request boundary, which the
application owns rather than the dispatcher. Call `Security-kit/runtime_screen.py`'s
`screen_input` there. SECURITY.md S1.6 carries the three-line wiring.

Three decisions worth arguing with:

1.  THE GATE IS THE ONE IN `permission.py`, NOT A SECOND COPY OF IT. `make_permission_check`
    is imported, so all four gates — protected paths, deny-list, phase gate, egress —
    apply to a deployed application with the same policy files and the same verdicts as
    a developer's session. A runtime-specific reimplementation would have been the third
    copy of a gate in this repo and the first one nothing tests.

2.  A CHECK THAT THROWS IS A DENIAL, NOT AN OUTAGE. `permission.py` raises `PolicyError`
    when a policy file is missing or corrupt, precisely so that a caller cannot mistake
    "no verdict" for "allowed" — the hook path converts it to exit 2. The equivalent here
    is to catch every exception out of the check and deny. Letting it propagate would be
    almost right and quietly wrong: the application's own error handling would decide
    what happens next, and the common shape (catch, log, continue) fails open.

3.  EVERY OUTCOME GETS AN AUDIT LINE, INCLUDING THE ALLOWS. Refusals are the interesting
    half but an audit trail of refusals only cannot answer "what did this agent do",
    which is the question an incident actually asks.

This file is in `BUILTIN_PROTECTED_PATHS`. It has to be: it is the single chokepoint
holding a deployed application's only call to the permission gate, so editing it
disables gate ② for the whole application in one line — strictly worse than editing any
hook adapter, which costs one developer their IDE session. Measured on dev_fengmin
2026-08-21, before that line existed: `Edit governance/runtime_dispatcher.py` was ALLOW.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# `permission` is a sibling. Adding this directory explicitly means an application can
# import the dispatcher by any route — `sys.path` entry, `importlib`, or from a parent
# package — without also having to know where the gate lives.
sys.path.insert(0, str(Path(__file__).parent))
from permission import make_permission_check, normalize_tool_name  # noqa: E402

# Both siblings are removed together by `install.sh --no-security`, so an unguarded
# import of either is exactly as safe as importing the permission gate above: a build
# that has the gate has the screen and the audit log too.
sys.path.insert(0, str(PROJECT_ROOT / "Harness-Best-Practice" / "observability"))
sys.path.insert(0, str(PROJECT_ROOT / "Security-kit"))
from audit import record            # noqa: E402
from runtime_screen import screen_result  # noqa: E402


class _PermissionBlock:
    """The shape `make_permission_check` expects: `.name` and `.input`.

    Claude Code hands the gate a tool-use block; in process there is no such object, so
    the dispatcher builds the two attributes the gate reads. Keeping the gate's signature
    unchanged is what lets one implementation serve both callers.
    """

    __slots__ = ("name", "input")

    def __init__(self, name: str, tool_input: dict):
        self.name = name
        self.input = tool_input


class RuntimeDispatcher:
    """The only way a deployed application should execute a registered tool.

        dispatcher = RuntimeDispatcher({"fetch_article": fetch_article})
        result = dispatcher.execute("fetch_article", {"url": "https://..."})

    Raises `PermissionError` when gate ② refuses, so a caller that forgets to check a
    return value still cannot proceed with a denied call.
    """

    def __init__(self, tools: dict, *, result_screen=screen_result):
        """`tools` maps a tool name to a callable taking keyword arguments.

        `result_screen` exists so an application can *extend* the ④ screen, not remove
        it: passing `None` raises rather than skipping the screen. An off switch on a
        data-plane control is the first thing an incident report finds, and a default
        argument is far too quiet a place to keep one. `demo/harness.py` and the
        `PostToolUse` hook screen unconditionally; so does this.
        """
        if result_screen is None:
            raise ValueError(
                "result_screen=None would disable gate ④ for every tool call. Pass a "
                "callable that wraps Security-kit/runtime_screen.py's screen_result if "
                "you need to extend it."
            )
        self._tools = dict(tools)
        self._permission_check = make_permission_check()
        self._result_screen = result_screen

    @property
    def tool_names(self) -> list:
        """Registered tool names, sorted. For assertions and for operator inspection."""
        return sorted(self._tools)

    def _deny(self, tool_name: str, args: dict, reason: str) -> "PermissionError":
        record("runtime_tool_call", tool_name, args, "DENIED", reason)
        return PermissionError(reason)

    def execute(self, tool_name: str, tool_input: dict | None = None):
        """Run one tool through ② → ③ → ④. Raises `PermissionError` if ② refuses."""
        args = dict(tool_input or {})

        # An unregistered name is refused before the gate, not after: the gate answers
        # questions about tools, and "this tool does not exist here" is a question about
        # the registry. It also keeps a typo from reaching a `**args` call.
        if tool_name not in self._tools:
            raise self._deny(tool_name, args,
                             f"runtime tool not registered: {tool_name}")

        block = _PermissionBlock(normalize_tool_name(tool_name), args)
        try:
            allowed, reason = self._permission_check(block)
        except Exception as exc:  # noqa: BLE001 — see decision 2
            raise self._deny(
                tool_name, args,
                f"runtime permission check failed closed: {type(exc).__name__}: {exc}",
            ) from exc

        if not allowed:
            raise self._deny(tool_name, args,
                             reason or f"runtime tool denied: {tool_name}")

        record("runtime_tool_call", tool_name, args, "ALLOWED",
               reason or "runtime policy allowed tool call")

        result = self._tools[tool_name](**args)      # ③
        return self._result_screen(result, tool_name)  # ④
