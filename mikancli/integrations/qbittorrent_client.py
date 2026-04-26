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
        response_text = self._open(
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
        version = self._open("/api/v2/app/version").strip()
        if not version:
            raise QBittorrentError("qBittorrent returned an empty version response.")
        return version

    def add_feed(self, feed_url: str, *, path: str | None = None) -> None:
        cleaned_feed_url = collapse_spaces(feed_url)
        if not cleaned_feed_url:
            raise QBittorrentError(
                "RSS feed URL is required before submitting to qBittorrent."
            )

        payload = {"url": cleaned_feed_url}
        cleaned_path = collapse_spaces(path or "")
        if cleaned_path:
            payload["path"] = cleaned_path

        self._open(
            "/api/v2/rss/addFeed",
            data=urlencode(payload).encode("utf-8"),
            content_type="application/x-www-form-urlencoded",
        )

    def set_auto_downloading_rule(
        self,
        rule_name: str,
        rule_definition: dict[str, object],
    ) -> None:
        cleaned_rule_name = collapse_spaces(rule_name)
        if not cleaned_rule_name:
            raise QBittorrentError(
                "RSS rule name is required before submitting to qBittorrent."
            )

        self._open(
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
        payload = self._open_json("/api/v2/rss/items?withData=false")
        if not isinstance(payload, dict):
            raise QBittorrentError(
                "qBittorrent returned an invalid RSS items response."
            )
        return payload

    def get_auto_downloading_rules(self) -> dict[str, object]:
        payload = self._open_json("/api/v2/rss/rules")
        if not isinstance(payload, dict):
            raise QBittorrentError(
                "qBittorrent returned an invalid RSS rules response."
            )
        return payload

    def verify_rule_draft(self, draft: RuleDraft) -> QBittorrentSubmissionResult:
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
        cleaned_feed_url = collapse_spaces(feed_url)
        if not cleaned_feed_url:
            return False
        return nested_value_contains(self.get_rss_items(), cleaned_feed_url)

    def _open(
        self,
        path: str,
        *,
        data: bytes | None = None,
        content_type: str | None = None,
    ) -> str:
        full_url = f"{self.settings.url}{path}"
        headers = {
            "Referer": f"{self.settings.url}/",
            "Origin": self._build_origin_header(),
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

    def _build_origin_header(self) -> str:
        parts = urlsplit(self.settings.url)
        return f"{parts.scheme}://{parts.netloc}"

    def _open_json(self, path: str) -> object:
        response_text = self._open(path)
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise QBittorrentError(
                f"qBittorrent returned invalid JSON for {path}."
            ) from exc


def normalize_qbittorrent_url(url: str) -> str:
    cleaned = collapse_spaces(url)
    if not cleaned:
        raise QBittorrentError("qBittorrent WebUI URL is required.")
    if "://" not in cleaned:
        cleaned = f"http://{cleaned}"
    return cleaned.rstrip("/")


def nested_value_contains(value: object, target: str) -> bool:
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
    rule = rules.get(collapse_spaces(rule_name))
    if not isinstance(rule, dict):
        return False

    affected_feeds = rule.get("affectedFeeds")
    if not isinstance(affected_feeds, list):
        return False
    return feed_url in affected_feeds
