"""Shared permission-gate entry point after the security-layer path migration.

The original gate implementation is kept unchanged in permission_impl.py. This adapter
sets the new project root and migrated protected paths, then re-exports the same API.
Keeping the gate logic unchanged avoids mixing a path migration with a security-logic
rewrite.
"""
import json
import sys
from pathlib import Path
import permission_impl as _impl

PROJECT_ROOT = Path(__file__).parents[2]
_impl.PROJECT_ROOT = PROJECT_ROOT
_impl.FEATURE_LIST_PATH = PROJECT_ROOT / "Harness-Best-Practice" / "feature_list.json"


def _migrate_protected_path(path: str) -> str:
    exact = {
        "governance/permission.py": "security/shared/permission.py",
        "governance/deny-list.json": "security/shared/deny-list.json",
        "governance/mcp-allowlist.json": "security/shared/mcp-allowlist.json",
        "Security-kit/secret_scan.py": "security/buildtime/secret_scan.py",
        "Security-kit/content_trust.py": "security/shared/content_trust.py",
        "Security-kit/prompt_screen.py": "security/buildtime/prompt_screen.py",
        "Security-kit/result_screen.py": "security/shared/result_screen.py",
        "governance/runtime_dispatcher.py": "security/runtime/runtime_dispatcher.py",
        "Security-kit/runtime_screen.py": "security/runtime/runtime_screen.py",
    }
    if path in exact:
        return exact[path]
    if path.startswith("Security-kit/runtime/"):
        return "security/runtime/core/" + path[len("Security-kit/runtime/"):]
    return path


_impl.BUILTIN_PROTECTED_PATHS = tuple(
    dict.fromkeys(
        [_migrate_protected_path(p) for p in _impl.BUILTIN_PROTECTED_PATHS]
        + [
            "security/shared/permission_impl.py",
            "security/shared/result_screen_impl.py",
            "security/runtime/__init__.py",
        ]
    )
)

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)
PROJECT_ROOT = _impl.PROJECT_ROOT
FEATURE_LIST_PATH = _impl.FEATURE_LIST_PATH
BUILTIN_PROTECTED_PATHS = _impl.BUILTIN_PROTECTED_PATHS


def _cli() -> None:
    def deny(reason: str):
        print(reason, file=sys.stderr)
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "Harness-Best-Practice" / "observability"))
            from audit import record
            record("PreToolUse", ctx["tool"], {}, "DENIED", reason)
        except Exception:
            pass
        raise SystemExit(2)

    ctx = {"tool": "unknown"}
    raw = sys.stdin.read().strip()
    if not raw:
        deny("permission gate: empty stdin (fail closed)")
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        deny("permission gate: malformed hook payload (fail closed)")
    if not isinstance(data, dict):
        deny("permission gate: unexpected hook payload shape (fail closed)")

    tool_input = data.get("tool_input", {})
    if not isinstance(tool_input, dict):
        tool_input = {}

    class Block:
        def __init__(self, name, input):
            self.name = name
            self.input = input

    ctx["tool"] = data.get("tool_name", "") or "unknown"
    block = Block(normalize_tool_name(data.get("tool_name", "")), tool_input)
    try:
        allowed, reason = make_permission_check()(block)
    except PolicyError as exc:
        deny(f"permission gate: {exc}")
    except Exception as exc:
        deny(f"permission gate: internal error ({type(exc).__name__}) (fail closed)")
    if not allowed:
        deny(reason)
    raise SystemExit(0)


if __name__ == "__main__":
    _cli()
