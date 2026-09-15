"""Runtime dispatcher — governed chokepoint for deployed tool execution.

The dispatcher uses the shared permission mechanism for position ②, executes the real
tool at ③, then applies the runtime result screen at ④. Unknown tools and policy errors
fail closed.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
SHARED_SECURITY = PROJECT_ROOT / "security" / "shared"
sys.path.insert(0, str(SHARED_SECURITY))
from permission import make_permission_check, normalize_tool_name  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "Harness-Best-Practice" / "observability"))
from audit import record  # noqa: E402

# runtime_screen.py is the runtime adapter in this directory.
sys.path.insert(0, str(Path(__file__).parent))
from runtime_screen import screen_result  # noqa: E402


class _PermissionBlock:
    """The shape `make_permission_check` expects: `.name` and `.input`."""

    __slots__ = ("name", "input")

    def __init__(self, name: str, tool_input: dict):
        self.name = name
        self.input = tool_input


class RuntimeDispatcher:
    """The only way a deployed application should execute a registered tool."""

    def __init__(self, tools: dict, *, result_screen=screen_result):
        if result_screen is None:
            raise ValueError(
                "result_screen=None would disable gate ④ for every tool call. Pass a "
                "callable that wraps security/runtime/runtime_screen.py's screen_result "
                "if you need to extend it."
            )
        self._tools = dict(tools)
        self._permission_check = make_permission_check()
        self._result_screen = result_screen

    @property
    def tool_names(self) -> list:
        return sorted(self._tools)

    def _deny(self, tool_name: str, args: dict, reason: str) -> "PermissionError":
        record("runtime_tool_call", tool_name, args, "DENIED", reason)
        return PermissionError(reason)

    def execute(self, tool_name: str, tool_input: dict | None = None):
        """Run one tool through ② → ③ → ④. Raises `PermissionError` if ② refuses."""
        args = dict(tool_input or {})

        if tool_name not in self._tools:
            raise self._deny(tool_name, args,
                             f"runtime tool not registered: {tool_name}")

        block = _PermissionBlock(normalize_tool_name(tool_name), args)
        try:
            allowed, reason = self._permission_check(block)
        except Exception as exc:
            raise self._deny(
                tool_name, args,
                f"runtime permission check failed closed: {type(exc).__name__}: {exc}",
            ) from exc

        if not allowed:
            raise self._deny(tool_name, args,
                             reason or f"runtime tool denied: {tool_name}")

        record("runtime_tool_call", tool_name, args, "ALLOWED",
               reason or "runtime policy allowed tool call")

        result = self._tools[tool_name](**args)
        return self._result_screen(result, tool_name)
