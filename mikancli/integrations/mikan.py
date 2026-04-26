from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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


def fetch_html(url: str, *, timeout: float = 15.0) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:  # pragma: no cover
        raise MikanLookupError(f"Mikan returned HTTP {exc.code} for {url}") from exc
    except URLError as exc:  # pragma: no cover
        reason = getattr(exc, "reason", exc)
        raise MikanLookupError(f"Could not reach Mikan: {reason}") from exc


def search_mikan_bangumi(keyword: str, *, timeout: float = 15.0) -> tuple[MikanBangumi, ...]:
    html = fetch_html(build_search_url(keyword), timeout=timeout)
    return parse_search_results(html)


def fetch_mikan_subgroups(
    bangumi_id: int,
    *,
    timeout: float = 15.0,
) -> tuple[MikanSubgroup, ...]:
    html = fetch_html(build_bangumi_page_url(bangumi_id), timeout=timeout)
    return parse_bangumi_subgroups(html, bangumi_id=bangumi_id)


def fetch_mikan_feed_items(
    feed_url: str,
    *,
    timeout: float = 15.0,
) -> tuple[MikanFeedItem, ...]:
    xml_text = fetch_html(feed_url, timeout=timeout)
    return parse_feed_items(xml_text)


def parse_feed_items(xml_text: str) -> tuple[MikanFeedItem, ...]:
    try:
        return parse_mikan_feed_items(xml_text)
    except MikanParseError as exc:
        raise MikanLookupError(str(exc)) from exc
