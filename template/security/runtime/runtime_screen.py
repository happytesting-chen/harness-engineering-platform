"""Runtime input/result screening for a deployed application.

Position ① screens external requests before the model. Position ④ screens tool output
before it returns to model context. Detection and result substitution are owned by the
shared security layer so build-time and runtime do not duplicate policy.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
SHARED_SECURITY = PROJECT_ROOT / "security" / "shared"
sys.path.insert(0, str(SHARED_SECURITY))
from content_trust import scan_text  # noqa: E402
from result_screen import screen as _screen_response  # noqa: E402

_MAX_MARKERS_SHOWN = 4


class InputRejected(Exception):
    """Position ① refused an external request."""

    def __init__(self, message: str, markers: list):
        super().__init__(message)
        self.markers = list(markers)


def _audit(event: str, subject: str, markers: list, decision: str, reason: str) -> None:
    """Best-effort audit line. Never allowed to change the verdict."""
    try:
        sys.path.insert(0, str(PROJECT_ROOT / "Harness-Best-Practice" / "observability"))
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
    """Gate ①. Return clean text unchanged; reject unscannable or hostile input."""
    if not isinstance(text, str):
        reason = (f"runtime input screen: expected str, got "
                  f"{type(text).__name__} — cannot screen (fail closed)")
        _audit("runtime_input", source, [], "DENIED", reason)
        raise InputRejected(reason, [])

    markers = scan_text(text)
    if not markers:
        return text

    reason = (f"runtime input screen: request rejected — instruction-shaped text "
              f"matched {len(markers)} marker(s): {_marker_summary(markers)}")
    _audit("runtime_input", source, markers, "DENIED", reason)
    raise InputRejected(reason, markers)


def screen_result(result, tool: str = "unknown"):
    """Gate ④. Return result, or a shape-preserving shared-security replacement."""
    markers, replacement = _screen_response(result, tool)
    if not markers:
        return result
    _audit("runtime_result", tool, markers, "WITHHELD",
           "instruction-shaped text in tool output")
    return replacement
