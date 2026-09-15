"""Test import bootstrap for the migrated security-layer layout."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for path in (
    PROJECT_ROOT / "security",
    PROJECT_ROOT / "security" / "runtime" / "core",
    PROJECT_ROOT / "security" / "runtime",
    PROJECT_ROOT / "security" / "buildtime",
    PROJECT_ROOT / "security" / "shared",
):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)
