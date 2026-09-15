"""Runtime security package.

Implementation modules remain physically grouped in runtime/core/. Extending the package
search path keeps the established `runtime.<module>` imports working without renaming the
modules during the directory migration.
"""
from pathlib import Path

_core = str(Path(__file__).parent / "core")
if _core not in __path__:
    __path__.append(_core)
