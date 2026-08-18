# ** newly added **
"""Application adapter for the reusable runtime security harness.

This module contains only project/framework wiring. Security authority stays in the
copied harness primitives under governance/ and Security-kit/, with runtime secret
screening kept in the dedicated application runtime scanner.
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
from audit import record
from src.runtime_secret_scan import scan_tool_input


# ** newly changed **
# content_trust.py intentionally returns compact regex identifiers. Translate those
# identifiers at the runtime adapter boundary into human-readable audit evidence so
# operators and the model do not have to infer why content was blocked.
def _describe_content_markers(markers: list[str]) -> list[str]:
    descriptions = []
    for marker in markers:
        if "ignore\\s+" in marker and "previous" in marker:
            descriptions.append("ignore previous/prior instructions")
        elif "disregard\\s+" in marker:
            descriptions.append("disregard previous policy/rules")
        elif "you\\s+are\\s+now" in marker:
            descriptions.append("role-redefinition instruction: 'you are now'")
        elif "system\\s*:" in marker:
            descriptions.append("system-style instruction marker")
        elif "admin|developer|root" in marker:
            descriptions.append("admin/developer/root mode instruction")
        elif "auto[-\\s]?approve|approve" in marker:
            descriptions.append("approval/override instruction")
        elif "set\\s+(confidence|decision|amount)" in marker:
            descriptions.append("instruction to set decision/confidence/amount")
        elif "new\\s+instructions" in marker:
            descriptions.append("new instructions directive")
        else:
            descriptions.append("instruction-shaped content")
    return list(dict.fromkeys(descriptions))
# ** newly changed **


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
            # ** newly changed **
            detected_patterns = _describe_content_markers(markers)
            reason = (
                "content-trust: suspicious external content blocked from model context; "
                "detected suspicious instruction-shaped content: "
                + "; ".join(detected_patterns)
            )
            record(
                "content_trust",
                "tool_result",
                {
                    "markers": markers,
                    "detected_patterns": detected_patterns,
                },
                "SUSPICIOUS",
                reason,
            )
            # ** newly changed **
            raise PermissionError(reason)
        return result

    def execute(self, tool_name, tool_input=None):
        """Runtime secret check -> permission/egress -> tool -> content trust."""
        args = dict(tool_input or {})

        reason = scan_tool_input(args)
        if reason:
            record("secret_check", tool_name, {}, "BLOCKED", reason)
            raise PermissionError(reason)

        return self._dispatcher.execute(tool_name, args)
# ** newly added **
