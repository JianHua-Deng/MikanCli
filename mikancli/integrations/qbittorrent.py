from __future__ import annotations

from dataclasses import dataclass
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener

from mikancli.core.models import QBittorrentSettings
from mikancli.core.normalize import collapse_spaces


class QBittorrentError(Exception):
    """Raised when qBittorrent WebUI setup or verification fails."""


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
            raise QBittorrentError(
                f"qBittorrent request failed with HTTP {exc.code} for {path}."
            ) from exc
        except URLError as exc:
            raise QBittorrentError(
                "Could not reach qBittorrent WebUI at "
                f"{self.settings.url}: {exc.reason}"
            ) from exc

    def _build_origin_header(self) -> str:
        parts = urlsplit(self.settings.url)
        return f"{parts.scheme}://{parts.netloc}"


def normalize_qbittorrent_url(url: str) -> str:
    cleaned = collapse_spaces(url)
    if not cleaned:
        raise QBittorrentError("qBittorrent WebUI URL is required.")
    if "://" not in cleaned:
        cleaned = f"http://{cleaned}"
    return cleaned.rstrip("/")


def check_connection(settings: QBittorrentSettings) -> str:
    client = QBittorrentClient(settings)
    has_credentials = bool(settings.username or settings.password)

    if has_credentials:
        try:
            client.login()
        except QBittorrentError as exc:
            if "HTTP 403" in str(exc):
                raise QBittorrentError(
                    "qBittorrent rejected the login request. Check the WebUI "
                    "username/password in qBittorrent settings and try again."
                ) from exc
            raise
    try:
        return client.get_version()
    except QBittorrentError as exc:
        message = str(exc)
        if not has_credentials and "HTTP 403" in message:
            raise QBittorrentError(
                "qBittorrent WebUI is reachable, but it requires a username and "
                "password. Enter the WebUI credentials from qBittorrent settings "
                "and try again."
            ) from exc
        raise
