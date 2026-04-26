from __future__ import annotations

from urllib.parse import quote

BASE_URL = "https://mikanani.me"
SEARCH_PATH = "/Home/Search?searchstr="


def build_bangumi_page_url(bangumi_id: int) -> str:
    return f"{BASE_URL}/Home/Bangumi/{bangumi_id}"


def build_bangumi_feed_url(bangumi_id: int) -> str:
    return f"{BASE_URL}/RSS/Bangumi?bangumiId={bangumi_id}"


def build_subgroup_feed_url(bangumi_id: int, subgroup_id: int) -> str:
    return f"{BASE_URL}/RSS/Bangumi?bangumiId={bangumi_id}&subgroupid={subgroup_id}"


def build_search_url(keyword: str) -> str:
    return f"{BASE_URL}{SEARCH_PATH}{quote(keyword)}"


def absolutize_mikan_url(path: str) -> str:
    if not path:
        return path
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{BASE_URL}{path}"
