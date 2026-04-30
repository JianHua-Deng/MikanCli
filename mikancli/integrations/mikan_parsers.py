from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import re
import xml.etree.ElementTree as ET

from mikancli.core.models import MikanBangumi, MikanFeedItem, MikanSubgroup
from mikancli.core.normalize import collapse_spaces
from mikancli.integrations.mikan_urls import (
    absolutize_mikan_url,
    build_bangumi_feed_url,
)

TORRENT_NAMESPACE = {"mikan": "https://mikanani.me/0.1/"}


class MikanParseError(RuntimeError):
    """Raised when Mikan HTML or RSS content cannot be parsed."""


def extract_bangumi_id(href: str) -> int | None:
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
        bangumi_id = extract_bangumi_id(href)
        if bangumi_id is None or bangumi_id in self._seen_ids:
            return

        self._inside_anchor = True
        self._anchor_depth = 1
        self._current = _CandidateBuffer(
            bangumi_id=bangumi_id,
            page_url=absolutize_mikan_url(href),
            text_parts=[],
        )

    def handle_endtag(self, tag: str) -> None:
        if self._inside_anchor:
            self._anchor_depth -= 1
            if self._anchor_depth == 0:
                self.finish_candidate()

        if not self._inside_candidate_list or tag != "ul":
            return

        self._candidate_list_depth -= 1
        if self._candidate_list_depth == 0:
            self._inside_candidate_list = False

    def handle_data(self, data: str) -> None:
        if self._inside_anchor and self._current is not None:
            self._current.text_parts.append(data)

    def finish_candidate(self) -> None:
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
    """
    Returns a tuple of MikanBangumi objects with ids, titles, page URLs, and feed URLs.
    Example: HTML containing '<a href="/Home/Bangumi/3560">Solo</a>' returns MikanBangumi(bangumi_id=3560, title="Solo", ...).
    """
    parser = _SearchResultParser()
    parser.feed(html)
    parser.close()
    return tuple(parser.candidates)


# These target the current Mikan Bangumi page markup. Keep them close to the
# parser so future markup fixes stay local.
_SUBGROUP_BLOCK_RE = re.compile(
    r'<div class="subgroup-text" id="(?P<subgroup_id>\d+)">(?P<body>.*?)</div>\s*<div class="episode-table">',
    re.DOTALL,
)
"""
Matches one subgroup section on a Mikan Bangumi page and captures its numeric subgroup id plus the inner HTML body.
It stops at the following episode table so each match contains one publish group area instead of the whole page.
Example: before '<div class="subgroup-text" id="370">...</div><div class="episode-table">' -> result subgroup_id="370", body="...".
"""
_PUBLISH_GROUP_RE = re.compile(
    r'<a href="(?P<href>/Home/PublishGroup/\d+)"[^>]*>(?P<title>.*?)</a>',
    re.DOTALL,
)
"""
Matches the publish-group link inside a subgroup block and captures both its relative URL and display title.
It is used after subgroup block extraction so the parser can name the subgroup and link back to the publisher page.
Example: before '<a href="/Home/PublishGroup/223">LoliHouse</a>' -> result href="/Home/PublishGroup/223", title="LoliHouse".
"""
_RSS_RE = re.compile(
    r'<a href="(?P<href>/RSS/Bangumi\?bangumiId=(?P<bangumi_id>\d+)(?:&|&amp;)subgroupid=(?P<subgroup_id>\d+))"[^>]*class="mikan-rss"',
    re.DOTALL,
)
"""
Matches a subgroup-specific Mikan RSS link and captures the full relative feed URL, Bangumi id, and subgroup id.
It accepts both plain ampersands and HTML-escaped ampersands because Mikan pages can contain either form.
Example: before '/RSS/Bangumi?bangumiId=3247&amp;subgroupid=370' -> result bangumi_id="3247", subgroup_id="370".
"""
_HTML_TAG_RE = re.compile(r"<[^>]+>")
"""
Matches a single HTML tag so markup can be removed from small title fragments before normalizing text.
It is intentionally simple because it only runs on already isolated snippets, not on the full page structure.
Example: before "<span>Prejudice-Studio</span>" -> result "Prejudice-Studio".
"""


def strip_tags(value: str) -> str:
    return collapse_spaces(unescape(_HTML_TAG_RE.sub(" ", value)))


def parse_bangumi_subgroups(html: str, *, bangumi_id: int) -> tuple[MikanSubgroup, ...]:
    """
    Parse a Bangumi page into subgroup-specific RSS feed choices.
    Returns only subgroups whose RSS link matches the requested Bangumi id.
    Example: a subgroup block with id="370" and title "LoliHouse" returns MikanSubgroup(subgroup_id=370, title="LoliHouse", ...).
    """
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

        title = strip_tags(publish_group_match.group("title"))
        if not title:
            continue

        subgroups.append(
            MikanSubgroup(
                subgroup_id=subgroup_id,
                title=title,
                feed_url=absolutize_mikan_url(
                    unescape(rss_match.group("href")).replace("&amp;", "&")
                ),
                publish_group_url=absolutize_mikan_url(
                    publish_group_match.group("href")
                ),
            )
        )
        seen_ids.add(subgroup_id)

    return tuple(subgroups)


def parse_feed_items(xml_text: str) -> tuple[MikanFeedItem, ...]:
    """
    Parse Mikan RSS XML into feed item metadata.
    Returns feed items with title, episode URL, torrent URL, content length, and publish time when available.
    Example: an RSS item with title "Episode 01" and enclosure length "1024" returns MikanFeedItem(title="Episode 01", content_length=1024, ...).
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise MikanParseError(f"Could not parse Mikan RSS feed: {exc}") from exc

    channel = root.find("channel")
    if channel is None:
        return ()

    items: list[MikanFeedItem] = []
    for item in channel.findall("item"):
        title = collapse_spaces(item.findtext("title", default=""))
        if not title:
            continue

        episode_url = absolutize_mikan_url(item.findtext("link", default=""))
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
            torrent_url = absolutize_mikan_url(enclosure_element.get("url") or "")

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
