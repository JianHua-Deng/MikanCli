from __future__ import annotations

import json
from dataclasses import dataclass
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

from mikancli.core.models import QBittorrentSettings, RuleDraft
from mikancli.core.normalize import collapse_spaces


class QBittorrentError(Exception):
    """Raised when qBittorrent WebUI setup or verification fails."""


@dataclass(frozen=True)
class QBittorrentSubmissionResult:
    feed_verified: bool
    rule_verified: bool

    @property
    def verified(self) -> bool:
        """Return True only when both the feed and the rule were found after submission. Returns False if either verification check failed."""
        return self.feed_verified and self.rule_verified


@dataclass
class QBittorrentClient:
    settings: QBittorrentSettings
    opener: object | None = None

    def __post_init__(self) -> None:
        self.settings = QBittorrentSettings(
            url=normalize_qbittorrent_url(self.settings.url),
            username=self.settings.username or None,
            password=self.settings.password or None,
        )
        if self.opener is None:
            self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def login(self) -> None:
        """Authenticate against the qBittorrent WebUI API using the configured credentials. Returns None on success or raises QBittorrentError when credentials are rejected."""
        response_text = self.open_text(
            "/api/v2/auth/login",
            data=urlencode(
                {
                    "username": self.settings.username or "",
                    "password": self.settings.password or "",
                }
            ).encode("utf-8"),
            content_type="application/x-www-form-urlencoded",
        )
        if response_text.strip().casefold() not in {"ok.", "ok"}:
            raise QBittorrentError(
                "qBittorrent rejected the WebUI username or password. Check the "
                "credentials in qBittorrent settings and try again."
            )

    def get_version(self) -> str:
        """Fetch the qBittorrent WebUI app version. Returns the version string or raises QBittorrentError when qBittorrent returns an empty response."""
        version = self.open_text("/api/v2/app/version").strip()
        if not version:
            raise QBittorrentError("qBittorrent returned an empty version response.")
        return version

    def add_feed(self, feed_url: str, *, path: str | None = None) -> None:
        """Add an RSS feed to qBittorrent, optionally under a feed folder path. Returns None on success or raises QBittorrentError when the feed URL is blank or the request fails."""
        cleaned_feed_url = collapse_spaces(feed_url)
        if not cleaned_feed_url:
            raise QBittorrentError(
                "RSS feed URL is required before submitting to qBittorrent."
            )

        payload = {"url": cleaned_feed_url}
        cleaned_path = collapse_spaces(path or "")
        if cleaned_path:
            payload["path"] = cleaned_path

        self.open_text(
            "/api/v2/rss/addFeed",
            data=urlencode(payload).encode("utf-8"),
            content_type="application/x-www-form-urlencoded",
        )

    def set_auto_downloading_rule(
        self,
        rule_name: str,
        rule_definition: dict[str, object],
    ) -> None:
        """Create or update a qBittorrent RSS auto-download rule. Returns None on success or raises QBittorrentError when the rule name is blank or the request fails."""
        cleaned_rule_name = collapse_spaces(rule_name)
        if not cleaned_rule_name:
            raise QBittorrentError(
                "RSS rule name is required before submitting to qBittorrent."
            )

        self.open_text(
            "/api/v2/rss/setRule",
            data=urlencode(
                {
                    "ruleName": cleaned_rule_name,
                    "ruleDef": json.dumps(rule_definition, ensure_ascii=False),
                }
            ).encode("utf-8"),
            content_type="application/x-www-form-urlencoded",
        )

    def get_rss_items(self) -> dict[str, object]:
        """Return the qBittorrent RSS item tree as a dictionary. Raises QBittorrentError when the WebUI returns invalid JSON or a non-object payload."""
        payload = self.open_json("/api/v2/rss/items?withData=false")
        if not isinstance(payload, dict):
            raise QBittorrentError(
                "qBittorrent returned an invalid RSS items response."
            )
        return payload

    def get_auto_downloading_rules(self) -> dict[str, object]:
        """Return qBittorrent RSS auto-download rules as a dictionary. Raises QBittorrentError when the WebUI returns invalid JSON or a non-object payload."""
        payload = self.open_json("/api/v2/rss/rules")
        if not isinstance(payload, dict):
            raise QBittorrentError(
                "qBittorrent returned an invalid RSS rules response."
            )
        return payload

    def verify_rule_draft(self, draft: RuleDraft) -> QBittorrentSubmissionResult:
        """
        Check whether qBittorrent contains the draft's feed URL and rule.
        Returns QBittorrentSubmissionResult with separate feed and rule verification flags.
        Example: when the feed exists but the rule does not, returns QBittorrentSubmissionResult(feed_verified=True, rule_verified=False).
        """
        if not draft.feed_url:
            raise QBittorrentError(
                "RSS feed URL is required before verifying qBittorrent."
            )

        rss_items = self.get_rss_items()
        rules = self.get_auto_downloading_rules()
        return QBittorrentSubmissionResult(
            feed_verified=nested_value_contains(rss_items, draft.feed_url),
            rule_verified=rules_contain_rule_for_feed(
                rules,
                rule_name=draft.rule_name,
                feed_url=draft.feed_url,
            ),
        )

    def has_feed_url(self, feed_url: str) -> bool:
        """Return whether qBittorrent already has a feed URL in its RSS tree. Returns False for blank feed URLs."""
        cleaned_feed_url = collapse_spaces(feed_url)
        if not cleaned_feed_url:
            return False
        return nested_value_contains(self.get_rss_items(), cleaned_feed_url)

    def open_text(
        self,
        path: str,
        *,
        data: bytes | None = None,
        content_type: str | None = None,
    ) -> str:
        full_url = f"{self.settings.url}{path}"
        headers = {
            "Referer": f"{self.settings.url}/",
            "Origin": self.build_origin_header(),
        }
        if content_type:
            headers["Content-Type"] = content_type
        request = Request(full_url, data=data, headers=headers)

        try:
            response = self.opener.open(request)
            return response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace").strip()
            suffix = f" Response: {body}" if body else ""
            raise QBittorrentError(
                f"qBittorrent request failed with HTTP {exc.code} for {path}.{suffix}"
            ) from exc
        except URLError as exc:
            raise QBittorrentError(
                "Could not reach qBittorrent WebUI at "
                f"{self.settings.url}: {exc.reason}"
            ) from exc

    def build_origin_header(self) -> str:
        parts = urlsplit(self.settings.url)
        return f"{parts.scheme}://{parts.netloc}"

    def open_json(self, path: str) -> object:
        response_text = self.open_text(path)
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise QBittorrentError(
                f"qBittorrent returned invalid JSON for {path}."
            ) from exc


def normalize_qbittorrent_url(url: str) -> str:
    """Normalize a qBittorrent WebUI URL by adding a scheme and removing trailing slashes. Example: normalize_qbittorrent_url("localhost:8080/") returns "http://localhost:8080"."""
    cleaned = collapse_spaces(url)
    if not cleaned:
        raise QBittorrentError("qBittorrent WebUI URL is required.")
    if "://" not in cleaned:
        cleaned = f"http://{cleaned}"
    return cleaned.rstrip("/")


def nested_value_contains(value: object, target: str) -> bool:
    """Search nested dicts and lists for a string value or matching dict key. Example: nested_value_contains({"feed": {"url": "x"}}, "x") returns True."""
    if isinstance(value, str):
        return value == target
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if key == target or nested_value_contains(nested_value, target):
                return True
    if isinstance(value, list):
        return any(nested_value_contains(item, target) for item in value)
    return False


def rules_contain_rule_for_feed(
    rules: dict[str, object],
    *,
    rule_name: str,
    feed_url: str,
) -> bool:
    """
    Return whether a qBittorrent rules payload has a named rule affecting a feed URL.
    Returns False when the rule is missing or its affectedFeeds field is not a list.
    Example: {"Solo": {"affectedFeeds": ["https://example.test/rss"]}} with rule_name="Solo" returns True for that feed URL.
    """
    rule = rules.get(collapse_spaces(rule_name))
    if not isinstance(rule, dict):
        return False

    affected_feeds = rule.get("affectedFeeds")
    if not isinstance(affected_feeds, list):
        return False
    return feed_url in affected_feeds
