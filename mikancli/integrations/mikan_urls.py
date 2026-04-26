from __future__ import annotations

from urllib.parse import quote

BASE_URL = "https://mikanani.me"
SEARCH_PATH = "/Home/Search?searchstr="


def build_bangumi_page_url(bangumi_id: int) -> str:
    """Build the Mikan Bangumi detail page URL for a Bangumi id. Example: build_bangumi_page_url(3560) returns "https://mikanani.me/Home/Bangumi/3560"."""
    return f"{BASE_URL}/Home/Bangumi/{bangumi_id}"


def build_bangumi_feed_url(bangumi_id: int) -> str:
    """Build the general RSS feed URL for a Bangumi id. Example: build_bangumi_feed_url(3560) returns "https://mikanani.me/RSS/Bangumi?bangumiId=3560"."""
    return f"{BASE_URL}/RSS/Bangumi?bangumiId={bangumi_id}"


def build_subgroup_feed_url(bangumi_id: int, subgroup_id: int) -> str:
    """Build the subgroup-specific RSS feed URL for a Bangumi id and subgroup id. Example: build_subgroup_feed_url(3247, 370) returns "https://mikanani.me/RSS/Bangumi?bangumiId=3247&subgroupid=370"."""
    return f"{BASE_URL}/RSS/Bangumi?bangumiId={bangumi_id}&subgroupid={subgroup_id}"


def build_search_url(keyword: str) -> str:
    """Build the Mikan search URL for a user keyword. Example: build_search_url("solo leveling") returns a URL ending in "searchstr=solo%20leveling"."""
    return f"{BASE_URL}{SEARCH_PATH}{quote(keyword)}"


def absolutize_mikan_url(path: str) -> str:
    """Convert a Mikan relative URL into an absolute URL while leaving absolute URLs unchanged. Example: absolutize_mikan_url("/Home/Bangumi/3560") returns "https://mikanani.me/Home/Bangumi/3560"."""
    if not path:
        return path
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{BASE_URL}{path}"
