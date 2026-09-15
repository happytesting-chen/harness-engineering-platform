"""Test import bootstrap for the migrated security-layer layout.

This keeps test modules focused on behavior while the authoritative implementation now
lives under security/{buildtime,runtime,shared}. Retired paths are not recreated.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for path in (
    PROJECT_ROOT / "security" / "runtime" / "core",
    PROJECT_ROOT / "security" / "runtime",
    PROJECT_ROOT / "security" / "buildtime",
    PROJECT_ROOT / "security" / "shared",
):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)
