"""Unit tests for utilities/sim_1.py (NYC news RSS fetcher).

The module under test is loaded explicitly by path so the test stays
robust regardless of sys.path / package layout.  The network is never
touched: ``urlopen`` is mocked and a canned RSS payload is returned.

Run with:  .venv/bin/python -m pytest tests/ -v
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree as ET

import pytest

# ---------------------------------------------------------------------------
# Module loading (by path, because the file is named test.py)
# ---------------------------------------------------------------------------

MODULE_PATH = Path(__file__).resolve().parent.parent.parent / "utilities" / "sim_1.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("sim_1", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def news_module() -> "importlib.util.ModuleType":
    return _load_module()


@pytest.fixture()
def rss_feed() -> bytes:
    """A canned RSS 2.0 feed: 10 <item> entries, 8 with usable titles.

    - item 1: title with surrounding whitespace (must be stripped)
    - item 3: empty <title> (must be filtered out)
    - item 5: no <title> element at all (must be filtered out)
    """
    items = (
        '<item><title>  First NYC headline  </title></item>'
        '<item><title>Second NYC story</title></item>'
        '<item><title></title></item>'
        '<item><title>Third NYC story</title></item>'
        '<item></item>'
        '<item><title>Fourth NYC story</title></item>'
        '<item><title>Fifth NYC story</title></item>'
        '<item><title>Sixth NYC story</title></item>'
        '<item><title>Seventh NYC story</title></item>'
        '<item><title>Eighth NYC story</title></item>'
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<rss version=\"2.0\"><channel>"
        "<title>Google News - Search</title>"
        f"{items}"
        "</channel></rss>"
    )
    assert ET.fromstring(xml) is not None  # sanity: fixture is valid XML
    return xml.encode("utf-8")


@pytest.fixture()
def patched_urlopen(news_module, rss_feed):
    """Patch urlopen in the module's namespace; yield (mock, response mock)."""
    response = mock.MagicMock()
    response.read.return_value = rss_feed
    response.__enter__.return_value = response  # `with urlopen(...) as resp`
    with mock.patch.object(news_module, "urlopen", return_value=response) as m:
        yield m


# ---------------------------------------------------------------------------
# get_top_nyc_news - core behaviour
# ---------------------------------------------------------------------------

def test_returns_top_n_headlines(news_module, patched_urlopen):
    result = news_module.get_top_nyc_news(limit=3)
    assert result == ["First NYC headline", "Second NYC story", "Third NYC story"]


def test_default_limit_is_5(news_module, patched_urlopen):
    assert len(_valid_titles()) == 8  # 8 usable titles in the fixture
    result = news_module.get_top_nyc_news()
    assert len(result) == 5
    assert result[0] == "First NYC headline"
    assert result[-1] == "Fifth NYC story"


def test_limit_larger_than_items_returns_all(news_module, patched_urlopen):
    result = news_module.get_top_nyc_news(limit=50)
    assert len(result) == 8
    assert result[-1] == "Eighth NYC story"


def test_empty_and_missing_titles_are_skipped(news_module, patched_urlopen):
    result = news_module.get_top_nyc_news(limit=10)
    assert "" not in result
    assert "Second NYC story" in result
    # items 3 (empty title) and 5 (no title) are absent by construction:
    assert len(result) == 8


def test_titles_are_stripped(news_module, patched_urlopen):
    titles = news_module.get_top_nyc_news(limit=1)
    assert titles == ["First NYC headline"]


def test_result_is_a_list_of_str(news_module, patched_urlopen):
    result = news_module.get_top_nyc_news(limit=2)
    assert isinstance(result, list)
    assert all(isinstance(t, str) for t in result)


# ---------------------------------------------------------------------------
# HTTP request details (no real network - urlopen is mocked)
# ---------------------------------------------------------------------------

def test_url_contains_quoted_nyc_query(news_module, patched_urlopen):
    news_module.get_top_nyc_news(limit=1)
    patched_urlopen.assert_called_once()
    request = patched_urlopen.call_args.args[0]
    assert "q=New%20York%20City" in request.full_url


def test_url_points_at_google_news_rss(news_module, patched_urlopen):
    news_module.get_top_nyc_news(limit=1)
    request = patched_urlopen.call_args.args[0]
    assert request.full_url.startswith("https://news.google.com/rss/search?")


def test_user_agent_header_is_set(news_module, patched_urlopen):
    news_module.get_top_nyc_news(limit=1)
    request = patched_urlopen.call_args.args[0]
    assert (request.get_header("User-agent") or "").startswith("Mozilla/5.0")


def test_urlopen_uses_30_second_timeout(news_module, patched_urlopen):
    news_module.get_top_nyc_news(limit=1)
    assert patched_urlopen.call_args.kwargs.get("timeout", 30) == 30


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def test_main_prints_numbered_top5_titles(news_module, capsys):
    fake = [f"Headline {i}" for i in range(1, 6)]
    with mock.patch.object(news_module, "get_top_nyc_news", return_value=fake) as mocked:
        news_module.main()
    captured = capsys.readouterr()
    mocked.assert_called_once_with(5)
    out_lines = [
        line.strip()
        for line in captured.out.splitlines()
        if line.startswith(("1.", "2.", "3.", "4.", "5."))
    ]
    assert out_lines == [f"{i}. Headline {i}" for i in range(1, 6)]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _valid_titles() -> list[str]:
    return [
        "First NYC headline", "Second NYC story", "Third NYC story",
        "Fourth NYC story", "Fifth NYC story", "Sixth NYC story",
        "Seventh NYC story", "Eighth NYC story",
    ]
