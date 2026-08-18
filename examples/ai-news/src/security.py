# ** newly added **
"""Application adapter for the reusable runtime security harness.

This module contains only project/framework wiring. Security authority stays in the
copied harness primitives under governance/ and Security-kit/.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECURITY_DIR = PROJECT_ROOT / "Security-kit"
OBSERVABILITY_DIR = PROJECT_ROOT / "Harness-Best-Practice" / "observability"

for path in (PROJECT_ROOT, SECURITY_DIR, OBSERVABILITY_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from governance.runtime_dispatcher import RuntimeDispatcher
from content_trust import scan_text
from secret_scan import scan_tool_input
from audit import record


class RuntimeSecurity:
    """Single application-facing entry point for secured tool execution."""

    def __init__(self, tools):
        self._dispatcher = RuntimeDispatcher(
            tools,
            result_screen=self._screen_result,
        )

    @staticmethod
    def _screen_result(result):
        """Block instruction-shaped external/tool output from returning to the model."""
        if isinstance(result, str):
            text = result
        else:
            text = json.dumps(result, ensure_ascii=False, default=str)

        markers = scan_text(text)
        if markers:
            reason = "content-trust: suspicious external content blocked from model context"
            record(
                "content_trust",
                "tool_result",
                {"markers": markers},
                "SUSPICIOUS",
                reason,
            )
            raise PermissionError(reason)
        return result

    def execute(self, tool_name, tool_input=None):
        """Secret check -> runtime dispatcher -> permission/egress -> tool -> content trust."""
        args = dict(tool_input or {})

        reason = scan_tool_input(args)
        if reason:
            record("secret_check", tool_name, {}, "BLOCKED", reason)
            raise PermissionError(reason)

        return self._dispatcher.execute(tool_name, args)
# ** newly added **
