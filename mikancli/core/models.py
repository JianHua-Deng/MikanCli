from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AppConfig:
    default_save_path: str | None = None
    qbittorrent_url: str | None = None
    qbittorrent_username: str | None = None
    qbittorrent_password: str | None = None


@dataclass(frozen=True)
class QBittorrentSettings:
    url: str
    username: str | None = None
    password: str | None = None


@dataclass(frozen=True)
class SearchRequest:
    keyword: str
    include_words: tuple[str, ...] = ()
    exclude_words: tuple[str, ...] = ()
    save_path: str | None = None


@dataclass(frozen=True)
class MikanBangumi:
    bangumi_id: int
    title: str
    page_url: str
    feed_url: str


@dataclass(frozen=True)
class MikanSubgroup:
    subgroup_id: int
    title: str
    feed_url: str
    publish_group_url: str | None = None


@dataclass(frozen=True)
class MikanFeedItem:
    title: str
    episode_url: str | None = None
    torrent_url: str | None = None
    content_length: int | None = None
    published_at: str | None = None


@dataclass(frozen=True)
class RuleDraft:
    keyword: str
    normalized_keyword: str
    rule_name: str
    must_contain: tuple[str, ...]
    must_not_contain: tuple[str, ...]
    mikan_title: str | None = None
    mikan_bangumi_id: int | None = None
    mikan_page_url: str | None = None
    mikan_subgroup: str | None = None
    mikan_subgroup_id: int | None = None
    mikan_publish_group_url: str | None = None
    feed_url: str | None = None
    save_path: str | None = None
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
