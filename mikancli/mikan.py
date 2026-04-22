from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from mikancli.models import MikanBangumi, MikanFeedItem, MikanSubgroup
from mikancli.normalize import collapse_spaces

BASE_URL = "https://mikanani.me"
SEARCH_PATH = "/Home/Search?searchstr="
USER_AGENT = "MikanCli/0.1 (+https://mikanani.me)"
TORRENT_NAMESPACE = {"mikan": "https://mikanani.me/0.1/"}


class MikanLookupError(RuntimeError):
    """Raised when a Mikan page cannot be fetched or parsed."""


def build_bangumi_page_url(bangumi_id: int) -> str:
    return f"{BASE_URL}/Home/Bangumi/{bangumi_id}"


def build_bangumi_feed_url(bangumi_id: int) -> str:
    return f"{BASE_URL}/RSS/Bangumi?bangumiId={bangumi_id}"


def build_subgroup_feed_url(bangumi_id: int, subgroup_id: int) -> str:
    return f"{BASE_URL}/RSS/Bangumi?bangumiId={bangumi_id}&subgroupid={subgroup_id}"


def build_search_url(keyword: str) -> str:
    return f"{BASE_URL}{SEARCH_PATH}{quote(keyword)}"


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


def _absolutize_url(path: str) -> str:
    if not path:
        return path
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{BASE_URL}{path}"


def _extract_bangumi_id(href: str) -> int | None:
    prefix = "/Home/Bangumi/"
    if not href.startswith(prefix):
        return None

    bangumi_id_text = href[len(prefix) :].split("?", maxsplit=1)[0].strip("/")
    if not bangumi_id_text.isdigit():
        return None

    return int(bangumi_id_text)


@dataclass
class _CandidateBuffer:
    bangumi_id: int
    page_url: str
    text_parts: list[str]


class _SearchResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.candidates: list[MikanBangumi] = []
        self._seen_ids: set[int] = set()
        self._inside_candidate_list = False
        self._candidate_list_depth = 0
        self._inside_anchor = False
        self._anchor_depth = 0
        self._current: _CandidateBuffer | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)

        if tag == "ul" and "an-ul" in (attr_map.get("class") or "").split():
            self._inside_candidate_list = True
            self._candidate_list_depth = 1
            return

        if self._inside_candidate_list and tag == "ul":
            self._candidate_list_depth += 1
            return

        if not self._inside_candidate_list or tag != "a":
            if self._inside_anchor and tag != "a":
                self._anchor_depth += 1
            return

        href = attr_map.get("href") or ""
        bangumi_id = _extract_bangumi_id(href)
        if bangumi_id is None or bangumi_id in self._seen_ids:
            return

        self._inside_anchor = True
        self._anchor_depth = 1
        self._current = _CandidateBuffer(
            bangumi_id=bangumi_id,
            page_url=_absolutize_url(href),
            text_parts=[],
        )

    def handle_endtag(self, tag: str) -> None:
        if self._inside_anchor:
            if tag == "a":
                self._anchor_depth -= 1
                if self._anchor_depth == 0:
                    self._finish_candidate()
            else:
                self._anchor_depth -= 1

        if not self._inside_candidate_list or tag != "ul":
            return

        self._candidate_list_depth -= 1
        if self._candidate_list_depth == 0:
            self._inside_candidate_list = False

    def handle_data(self, data: str) -> None:
        if self._inside_anchor and self._current is not None:
            self._current.text_parts.append(data)

    def _finish_candidate(self) -> None:
        if self._current is None:
            self._inside_anchor = False
            return

        title = collapse_spaces(unescape(" ".join(self._current.text_parts)))
        if title:
            self.candidates.append(
                MikanBangumi(
                    bangumi_id=self._current.bangumi_id,
                    title=title,
                    page_url=self._current.page_url,
                    feed_url=build_bangumi_feed_url(self._current.bangumi_id),
                )
            )
            self._seen_ids.add(self._current.bangumi_id)

        self._current = None
        self._inside_anchor = False


def parse_search_results(html: str) -> tuple[MikanBangumi, ...]:
    parser = _SearchResultParser()
    parser.feed(html)
    parser.close()
    return tuple(parser.candidates)


_SUBGROUP_BLOCK_RE = re.compile(
    r'<div class="subgroup-text" id="(?P<subgroup_id>\d+)">(?P<body>.*?)</div>\s*<div class="episode-table">',
    re.DOTALL,
)
_PUBLISH_GROUP_RE = re.compile(
    r'<a href="(?P<href>/Home/PublishGroup/\d+)"[^>]*>(?P<title>.*?)</a>',
    re.DOTALL,
)
_RSS_RE = re.compile(
    r'<a href="(?P<href>/RSS/Bangumi\?bangumiId=(?P<bangumi_id>\d+)(?:&|&amp;)subgroupid=(?P<subgroup_id>\d+))"[^>]*class="mikan-rss"',
    re.DOTALL,
)


def _strip_tags(value: str) -> str:
    return collapse_spaces(unescape(re.sub(r"<[^>]+>", " ", value)))


def parse_bangumi_subgroups(html: str, *, bangumi_id: int) -> tuple[MikanSubgroup, ...]:
    subgroups: list[MikanSubgroup] = []
    seen_ids: set[int] = set()

    for match in _SUBGROUP_BLOCK_RE.finditer(html):
        subgroup_id = int(match.group("subgroup_id"))
        if subgroup_id in seen_ids:
            continue

        body = match.group("body")
        publish_group_match = _PUBLISH_GROUP_RE.search(body)
        rss_match = _RSS_RE.search(body)
        if publish_group_match is None or rss_match is None:
            continue

        rss_bangumi_id = int(rss_match.group("bangumi_id"))
        rss_subgroup_id = int(rss_match.group("subgroup_id"))
        if rss_bangumi_id != bangumi_id or rss_subgroup_id != subgroup_id:
            continue

        title = _strip_tags(publish_group_match.group("title"))
        if not title:
            continue

        subgroups.append(
            MikanSubgroup(
                subgroup_id=subgroup_id,
                title=title,
                feed_url=_absolutize_url(unescape(rss_match.group("href")).replace("&amp;", "&")),
                publish_group_url=_absolutize_url(publish_group_match.group("href")),
            )
        )
        seen_ids.add(subgroup_id)

    return tuple(subgroups)


def parse_feed_items(xml_text: str) -> tuple[MikanFeedItem, ...]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise MikanLookupError(f"Could not parse Mikan RSS feed: {exc}") from exc

    channel = root.find("channel")
    if channel is None:
        return ()

    items: list[MikanFeedItem] = []
    for item in channel.findall("item"):
        title = collapse_spaces(item.findtext("title", default=""))
        if not title:
            continue

        episode_url = _absolutize_url(item.findtext("link", default=""))
        torrent_element = item.find("mikan:torrent", TORRENT_NAMESPACE)
        enclosure_element = item.find("enclosure")

        content_length_text = None
        published_at = None
        if torrent_element is not None:
            content_length_text = torrent_element.findtext(
                "mikan:contentLength",
                default="",
                namespaces=TORRENT_NAMESPACE,
            )
            published_at = collapse_spaces(
                torrent_element.findtext(
                    "mikan:pubDate",
                    default="",
                    namespaces=TORRENT_NAMESPACE,
                )
            ) or None

        if not content_length_text and enclosure_element is not None:
            content_length_text = enclosure_element.get("length")

        content_length = None
        if content_length_text and str(content_length_text).isdigit():
            content_length = int(content_length_text)

        torrent_url = None
        if enclosure_element is not None:
            torrent_url = _absolutize_url(enclosure_element.get("url") or "")

        items.append(
            MikanFeedItem(
                title=title,
                episode_url=episode_url or None,
                torrent_url=torrent_url or None,
                content_length=content_length,
                published_at=published_at,
            )
        )

    return tuple(items)


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
