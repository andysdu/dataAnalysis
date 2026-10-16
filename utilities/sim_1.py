"""Fetch the top 5 current New York City news headlines (Google News RSS)."""

import xml.etree.ElementTree as ET
from urllib.parse import quote
from urllib.request import Request, urlopen

FEED_URL = (
    "https://news.google.com/rss/search?"
    "q={query}&hl=en-US&gl=US&ceid=US:en"
)


def get_top_nyc_news(limit: int = 5) -> list[str]:
    """Return the top `limit` latest New York City headlines."""
    url = FEED_URL.format(query=quote("New York City"))
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (news-fetcher)"})
    with urlopen(req, timeout=30) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    titles = [
        item.findtext("title", "").strip()
        for item in root.findall(".//item")
        if item.findtext("title")
    ]
    return titles[:limit]


def main() -> None:
    print("Top 5 New York City news today:\n")
    for i, title in enumerate(get_top_nyc_news(5), start=1):
        print(f"{i}. {title}")


if __name__ == "__main__":
    main()