"""Shared result-screen entry point after the security-layer path migration.

The screening implementation is kept unchanged in result_screen_impl.py; this adapter
corrects the project-root location and preserves the established import and CLI API.
"""
from pathlib import Path
import result_screen_impl as _impl

_impl.PROJECT_ROOT = Path(__file__).parents[2]

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)
PROJECT_ROOT = _impl.PROJECT_ROOT

if __name__ == "__main__":
    _impl.main()
