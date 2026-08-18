"""Local digest persistence handler.

This is a raw handler and must be invoked through RuntimeSecurity.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
DIGEST_PATH = RUNTIME_DIR / "latest_digest.md"


def save_digest(content: str) -> dict:
    """Persist the current digest to the project's runtime directory."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    DIGEST_PATH.write_text(content, encoding="utf-8")
    return {
        "saved": True,
        "path": str(DIGEST_PATH.relative_to(PROJECT_ROOT)),
        "characters": len(content),
    }
