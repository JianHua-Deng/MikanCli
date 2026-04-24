from __future__ import annotations

import unittest
from urllib.error import HTTPError, URLError

from mikancli.core.models import QBittorrentSettings
from mikancli.integrations.qbittorrent import (
    QBittorrentError,
    check_connection,
    normalize_qbittorrent_url,
)


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self.body = body

    def read(self) -> bytes:
        return self.body.encode("utf-8")


class _FakeOpener:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.requests = []

    def open(self, request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class QBittorrentIntegrationTests(unittest.TestCase):
    def test_normalize_qbittorrent_url_adds_scheme_and_strips_trailing_slash(self) -> None:
        self.assertEqual(
            normalize_qbittorrent_url("localhost:8080/"),
            "http://localhost:8080",
        )

    def test_check_connection_logs_in_then_fetches_version(self) -> None:
        from unittest.mock import patch

        opener = _FakeOpener([_FakeResponse("Ok."), _FakeResponse("5.0.0")])

        with patch("mikancli.integrations.qbittorrent.build_opener", return_value=opener):
            version = check_connection(
                QBittorrentSettings(
                    url="localhost:8080",
                    username="admin",
                    password="secret",
                )
            )

        self.assertEqual(version, "5.0.0")
        self.assertEqual(len(opener.requests), 2)
        self.assertTrue(opener.requests[0].full_url.endswith("/api/v2/auth/login"))
        self.assertTrue(opener.requests[1].full_url.endswith("/api/v2/app/version"))

    def test_check_connection_accepts_empty_credentials_when_local_access_works(self) -> None:
        from unittest.mock import patch

        opener = _FakeOpener([_FakeResponse("5.0.0")])

        with patch("mikancli.integrations.qbittorrent.build_opener", return_value=opener):
            version = check_connection(
                QBittorrentSettings(
                    url="http://localhost:8080",
                    username="",
                    password="",
                )
            )

        self.assertEqual(version, "5.0.0")
        self.assertEqual(len(opener.requests), 1)
        self.assertTrue(opener.requests[0].full_url.endswith("/api/v2/app/version"))

    def test_check_connection_raises_helpful_error_when_webui_is_unreachable(self) -> None:
        from unittest.mock import patch

        opener = _FakeOpener([URLError("connection refused")])

        with patch("mikancli.integrations.qbittorrent.build_opener", return_value=opener):
            with self.assertRaisesRegex(
                QBittorrentError,
                "Could not reach qBittorrent WebUI",
            ):
                check_connection(QBittorrentSettings(url="localhost:8080"))

    def test_check_connection_raises_helpful_error_when_auth_is_required(self) -> None:
        from unittest.mock import patch

        opener = _FakeOpener(
            [HTTPError("http://localhost:8080/api/v2/app/version", 403, "Forbidden", {}, None)]
        )

        with patch("mikancli.integrations.qbittorrent.build_opener", return_value=opener):
            with self.assertRaisesRegex(
                QBittorrentError,
                "requires a username and password",
            ):
                check_connection(QBittorrentSettings(url="localhost:8080"))

    def test_check_connection_raises_helpful_error_when_credentials_are_wrong(self) -> None:
        from unittest.mock import patch

        opener = _FakeOpener([_FakeResponse("Fails.")])

        with patch("mikancli.integrations.qbittorrent.build_opener", return_value=opener):
            with self.assertRaisesRegex(
                QBittorrentError,
                "rejected the WebUI username or password",
            ):
                check_connection(
                    QBittorrentSettings(
                        url="localhost:8080",
                        username="admin",
                        password="wrong",
                    )
                )


if __name__ == "__main__":
    unittest.main()
