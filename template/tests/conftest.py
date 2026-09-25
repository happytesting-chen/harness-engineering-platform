"""Test import bootstrap for the security-layer layout.

Path notes:
- Patch `permission_impl.*`, NOT `permission.*`. permission.py re-exports values
  (copies), not references. Patching permission.py does not affect what
  permission_impl.py reads at call time. Always patch the impl directly:
      import permission_impl as _impl
      _impl.ALLOWLIST_PATH = fake_path

- Product source code belongs in src/<project_name>/. When your project adds a
  src/ directory, add it here so mock.patch() targets resolve correctly:
      sys.path.insert(0, str(PROJECT_ROOT / "src"))
      sys.path.insert(0, str(PROJECT_ROOT / "src" / "<project_name>"))
  Both are needed: flat imports work in production; mock.patch("project.module.fn")
  requires the full package path (src/ on sys.path) to replace the right reference.
"""
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
