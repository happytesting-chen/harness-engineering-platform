# ** newly added **
"""Minimal runtime tool dispatcher.

The deployed agent/orchestrator should call this dispatcher instead of calling
raw tool functions directly. The existing permission engine is evaluated before
each tool executes. An optional result-screen callback can screen untrusted tool
output before it is returned to the agent.
"""

from pathlib import Path
import sys

from governance.permission import make_permission_check, normalize_tool_name

# *** newly changed ***
# Reuse the existing observability recorder for deployed runtime tool decisions.
_OBSERVABILITY_DIR = Path(__file__).parent.parent / "Harness-Best-Practice" / "observability"
if str(_OBSERVABILITY_DIR) not in sys.path:
    sys.path.insert(0, str(_OBSERVABILITY_DIR))
from audit import record
# *** newly changed ***


class _PermissionBlock:
    """Minimal adapter for the existing permission.py interface."""

    def __init__(self, name, tool_input):
        self.name = name
        self.input = tool_input


class RuntimeDispatcher:
    """Single runtime path: permission check, tool execution, optional result screen."""

    def __init__(self, tools, result_screen=None):
        self._tools = dict(tools)
        self._permission_check = make_permission_check()
        self._result_screen = result_screen

    def execute(self, tool_name, tool_input=None):
        args = dict(tool_input or {})

        if tool_name not in self._tools:
            # *** newly changed ***
            reason = f"runtime tool not registered: {tool_name}"
            record("tool_call", tool_name, args, "DENIED", reason)
            # *** newly changed ***
            raise PermissionError(reason)

        block = _PermissionBlock(normalize_tool_name(tool_name), args)

        try:
            allowed, reason = self._permission_check(block)
        except Exception as exc:
            # Runtime permission failures must fail closed.
            # *** newly changed ***
            reason = f"runtime permission check failed closed: {exc}"
            record("tool_call", tool_name, args, "DENIED", reason)
            # *** newly changed ***
            raise PermissionError(reason) from exc

        if not allowed:
            # *** newly changed ***
            reason = reason or f"runtime tool denied: {tool_name}"
            record("tool_call", tool_name, args, "DENIED", reason)
            # *** newly changed ***
            raise PermissionError(reason)

        # *** newly changed ***
        allow_reason = reason or "runtime policy allowed tool call"
        record("tool_call", tool_name, args, "ALLOWED", allow_reason)
        # *** newly changed ***
        result = self._tools[tool_name](**args)

        if self._result_screen is not None:
            result = self._result_screen(result)

        return result

# ** newly added **
