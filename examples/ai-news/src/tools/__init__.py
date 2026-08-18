"""Raw application tool handlers.

These handlers are deliberately not agent-facing. The agent must call them only through
`src.security.RuntimeSecurity`, which performs runtime secret, permission/egress,
and content-trust checks around execution.
"""

from .digest import save_digest
from .github_trending import get_trending_repos
from .news import fetch_news


def build_tool_handlers():
    """Return the raw handler registry consumed by RuntimeSecurity."""
    return {
        "fetch_news": fetch_news,
        "get_trending_repos": get_trending_repos,
        "save_digest": save_digest,
    }
