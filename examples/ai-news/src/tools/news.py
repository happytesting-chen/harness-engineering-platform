"""News retrieval handler for approved external sources.

Security note: this is a raw handler. The agent must not call it directly; it is
registered behind RuntimeSecurity. Redirects are not followed automatically so an
approved URL cannot silently redirect the runtime to an unapproved destination.
"""

from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

_MAX_BYTES = 250_000
_MAX_TEXT_CHARS = 40_000


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip = 0
        self._title = False
        self.title_parts = []
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip += 1
        elif tag == "title" and self._skip == 0:
            self._title = True

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._title = False

    def handle_data(self, data):
        if self._skip:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._title:
            self.title_parts.append(text)
        self.text_parts.append(text)


def _extract_visible_text(raw: str) -> tuple[str, str]:
    parser = _VisibleTextParser()
    parser.feed(raw)
    title = " ".join(parser.title_parts).strip()
    text = "\n".join(parser.text_parts).strip()
    return title[:500], text[:_MAX_TEXT_CHARS]


def fetch_news(url: str) -> dict:
    """Fetch one approved news URL and return compact visible text.

    Egress approval is performed by RuntimeSecurity/permission.py before this handler
    starts. Automatic redirects are disabled to prevent redirect-based egress bypass.
    """
    request = Request(
        url,
        headers={
            "User-Agent": "AI-News-Runtime-Demo/1.0",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
        },
    )
    opener = build_opener(_NoRedirect())
    try:
        response = opener.open(request, timeout=15)
    except HTTPError as exc:
        if 300 <= exc.code < 400:
            location = exc.headers.get("Location", "")
            raise RuntimeError(
                f"redirect blocked before follow; request the redirected URL through the secured runtime path: {location}"
            ) from exc
        raise

    with response:
        content_type = response.headers.get("Content-Type", "")
        final_url = response.geturl()
        raw_bytes = response.read(_MAX_BYTES)
        charset = response.headers.get_content_charset() or "utf-8"

    raw = raw_bytes.decode(charset, errors="replace")
    if "html" in content_type.lower() or "<html" in raw[:1000].lower():
        title, text = _extract_visible_text(raw)
    else:
        title, text = "", raw[:_MAX_TEXT_CHARS]

    return {
        "source_url": url,
        "final_url": final_url,
        "title": title,
        "content": text,
    }
