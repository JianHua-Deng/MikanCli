from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from mikancli.core.models import MikanBangumi, MikanFeedItem, MikanSubgroup
from mikancli.integrations.mikan_parsers import (
    MikanParseError,
    parse_bangumi_subgroups,
    parse_feed_items as parse_mikan_feed_items,
    parse_search_results,
)
from mikancli.integrations.mikan_urls import (
    build_bangumi_feed_url,
    build_bangumi_page_url,
    build_search_url,
    build_subgroup_feed_url,
)

USER_AGENT = "MikanCli/0.1 (+https://mikanani.me)"


class MikanLookupError(RuntimeError):
    """Raised when a Mikan page cannot be fetched or parsed."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "UPSTREAM_ERROR",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def fetch_html(url: str, *, timeout: float = 15.0) -> str:
    """Fetch a Mikan page or feed as decoded UTF-8 text. Returns the response body, or raises MikanLookupError for HTTP and network failures."""
    request = Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        exc.close()
        code = "UPSTREAM_ERROR"
        retryable = False
        if exc.code == 408:
            code, retryable = "TIMEOUT", True
        elif 500 <= exc.code <= 599:
            code, retryable = "NETWORK_ERROR", True
        raise MikanLookupError(
            f"Mikan returned HTTP {exc.code}.",
            code=code,
            retryable=retryable,
        ) from exc
    except URLError as exc:
        timed_out = isinstance(exc.reason, TimeoutError)
        raise MikanLookupError(
            "Mikan request timed out." if timed_out else "Could not reach Mikan.",
            code="TIMEOUT" if timed_out else "NETWORK_ERROR",
            retryable=True,
        ) from exc
    except TimeoutError as exc:
        raise MikanLookupError(
            "Mikan request timed out.", code="TIMEOUT", retryable=True
        ) from exc
    except OSError as exc:
        raise MikanLookupError(
            "Could not complete the Mikan request.",
            code="NETWORK_ERROR",
            retryable=True,
        ) from exc


def search_mikan_bangumi(keyword: str, *, timeout: float = 15.0) -> tuple[MikanBangumi, ...]:
    """Search Mikan and return matching Bangumi candidates. Returns an empty tuple when the page has no parseable search results."""
    html = fetch_html(build_search_url(keyword), timeout=timeout)
    return parse_search_results(html)


def fetch_mikan_subgroups(bangumi_id: int, *, timeout: float = 15.0) -> tuple[MikanSubgroup, ...]:
    """Fetch subgroup-specific RSS options for a Bangumi id. Returns an empty tuple when the page has no parseable subgroup feeds."""
    html = fetch_html(build_bangumi_page_url(bangumi_id), timeout=timeout)
    return parse_bangumi_subgroups(html, bangumi_id=bangumi_id)


def fetch_mikan_feed_items(feed_url: str, *, timeout: float = 15.0) -> tuple[MikanFeedItem, ...]:
    """Fetch and parse recent items from a Mikan RSS feed. Returns an empty tuple when the feed has no parseable items."""
    xml_text = fetch_html(feed_url, timeout=timeout)
    return parse_feed_items(xml_text)


def parse_feed_items(xml_text: str) -> tuple[MikanFeedItem, ...]:
    """Parse Mikan RSS XML and convert parser errors into MikanLookupError. Returns parsed feed items, or an empty tuple for a valid feed with no items."""
    try:
        # A proxy or login page can be valid XML while being an invalid RSS
        # response. Keep that distinct from a valid feed with zero releases.
        root = ET.fromstring(xml_text)
        if root.tag != "rss" or root.find("channel") is None:
            raise MikanLookupError(
                "Mikan returned an invalid RSS feed.", code="INVALID_RESPONSE"
            )
        return parse_mikan_feed_items(xml_text)
    except (MikanParseError, ET.ParseError) as exc:
        raise MikanLookupError(
            "Could not parse the Mikan RSS feed.", code="INVALID_RESPONSE"
        ) from exc
