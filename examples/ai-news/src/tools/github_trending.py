"""GitHub trend signal handler.

This uses recently created, highly starred repositories as a transparent proxy for
fast-rising interest. It does not claim to measure exact week-over-week star velocity.
The handler is raw and must execute only behind RuntimeSecurity.
"""

import json
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_MAX_ITEMS = 10


def get_trending_repos(endpoint: str, days: int = 7) -> list[dict]:
    """Return recently created, highly starred AI/security repositories.

    `endpoint` is explicit so permission.py can validate the network destination
    before this handler executes. Expected v1 endpoint:
    https://api.github.com/search/repositories
    """
    days = max(1, min(int(days), 30))
    since = date.today() - timedelta(days=days)
    query = f"(ai OR llm OR security) created:>={since.isoformat()}"
    url = endpoint.rstrip("?") + "?" + urlencode(
        {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": _MAX_ITEMS,
        }
    )
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "AI-News-Runtime-Demo/1.0",
        },
    )
    with urlopen(request, timeout=15) as response:
        payload = json.load(response)

    results = []
    for item in payload.get("items", [])[:_MAX_ITEMS]:
        results.append(
            {
                "name": item.get("full_name"),
                "description": item.get("description") or "",
                "stars": int(item.get("stargazers_count") or 0),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "url": item.get("html_url"),
                "language": item.get("language"),
            }
        )
    return results
