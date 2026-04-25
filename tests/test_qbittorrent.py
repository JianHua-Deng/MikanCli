from __future__ import annotations

import json
import unittest
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs

from mikancli.core.models import QBittorrentSettings, RuleDraft
from mikancli.integrations.qbittorrent import (
    QBittorrentClient,
    QBittorrentError,
    build_qbittorrent_rule_definition,
    check_connection,
    normalize_qbittorrent_url,
    submit_rule_draft,
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

    def test_add_feed_posts_feed_url_and_path_to_rss_endpoint(self) -> None:
        opener = _FakeOpener([_FakeResponse("")])
        client = QBittorrentClient(
            QBittorrentSettings(url="localhost:8080"),
            opener=opener,
        )

        client.add_feed(
            " https://mikanani.me/RSS/Bangumi?bangumiId=3560&subgroupid=1230 ",
            path=" Mikan\\Solo Leveling ",
        )

        self.assertEqual(len(opener.requests), 1)
        request = opener.requests[0]
        self.assertTrue(request.full_url.endswith("/api/v2/rss/addFeed"))
        self.assertEqual(
            request.headers["Content-type"],
            "application/x-www-form-urlencoded",
        )
        body = parse_qs(request.data.decode("utf-8"))
        self.assertEqual(
            body["url"],
            ["https://mikanani.me/RSS/Bangumi?bangumiId=3560&subgroupid=1230"],
        )
        self.assertEqual(body["path"], ["Mikan\\Solo Leveling"])

    def test_build_qbittorrent_rule_definition_maps_draft_to_webui_shape(self) -> None:
        rule_definition = build_qbittorrent_rule_definition(
            RuleDraft(
                keyword="Solo Leveling",
                normalized_keyword="solo leveling",
                rule_name="Solo Leveling",
                must_contain=("HEVC", "1080p"),
                must_not_contain=("720p",),
                feed_url="https://mikanani.me/RSS/Bangumi?bangumiId=3560&subgroupid=1230",
                save_path="D:\\Anime\\Solo Leveling",
            ),
            add_paused=True,
            assigned_category=" Anime ",
        )

        self.assertEqual(
            rule_definition,
            {
                "enabled": True,
                "mustContain": "(?=.*HEVC)(?=.*1080p).*",
                "mustNotContain": "720p",
                "useRegex": True,
                "episodeFilter": "",
                "smartFilter": False,
                "previouslyMatchedEpisodes": [],
                "affectedFeeds": [
                    "https://mikanani.me/RSS/Bangumi?bangumiId=3560&subgroupid=1230"
                ],
                "ignoreDays": 0,
                "lastMatch": "",
                "addPaused": True,
                "assignedCategory": "Anime",
                "savePath": "D:\\Anime\\Solo Leveling",
            },
        )

    def test_set_auto_downloading_rule_posts_json_encoded_rule_definition(self) -> None:
        opener = _FakeOpener([_FakeResponse("")])
        client = QBittorrentClient(
            QBittorrentSettings(url="http://localhost:8080"),
            opener=opener,
        )
        rule_definition = {
            "enabled": True,
            "mustContain": "HEVC",
            "mustNotContain": "",
            "useRegex": False,
            "episodeFilter": "",
            "smartFilter": False,
            "previouslyMatchedEpisodes": [],
            "affectedFeeds": ["https://example.test/feed.xml"],
            "ignoreDays": 0,
            "lastMatch": "",
            "addPaused": False,
            "assignedCategory": "",
            "savePath": "D:\\Anime",
        }

        client.set_auto_downloading_rule(" Solo Leveling ", rule_definition)

        self.assertEqual(len(opener.requests), 1)
        request = opener.requests[0]
        self.assertTrue(request.full_url.endswith("/api/v2/rss/setRule"))
        body = parse_qs(request.data.decode("utf-8"))
        self.assertEqual(body["ruleName"], ["Solo Leveling"])
        self.assertEqual(json.loads(body["ruleDef"][0]), rule_definition)

    def test_submit_rule_draft_logs_in_adds_feed_then_sets_rule(self) -> None:
        from unittest.mock import patch

        feed_url = "https://mikanani.me/RSS/Bangumi?bangumiId=3560&subgroupid=1230"
        opener = _FakeOpener(
            [
                _FakeResponse("Ok."),
                _FakeResponse(""),
                _FakeResponse(""),
                _FakeResponse(
                    json.dumps(
                        {
                            "Mikan": {
                                "Solo Leveling": {
                                    "url": feed_url,
                                }
                            }
                        }
                    )
                ),
                _FakeResponse(
                    json.dumps(
                        {
                            "Solo Leveling": {
                                "affectedFeeds": [feed_url],
                            }
                        }
                    )
                ),
            ]
        )

        with patch("mikancli.integrations.qbittorrent.build_opener", return_value=opener):
            result = submit_rule_draft(
                QBittorrentSettings(
                    url="localhost:8080",
                    username="admin",
                    password="secret",
                ),
                RuleDraft(
                    keyword="Solo Leveling",
                    normalized_keyword="solo leveling",
                    rule_name="Solo Leveling",
                    must_contain=("HEVC",),
                    must_not_contain=("720p",),
                    feed_url=feed_url,
                    save_path="D:\\Anime\\Solo Leveling",
                ),
                feed_path="Mikan\\Solo Leveling",
            )

        self.assertTrue(result.verified)
        self.assertTrue(result.feed_verified)
        self.assertTrue(result.rule_verified)
        self.assertEqual(len(opener.requests), 5)
        self.assertTrue(opener.requests[0].full_url.endswith("/api/v2/auth/login"))
        self.assertTrue(opener.requests[1].full_url.endswith("/api/v2/rss/addFeed"))
        self.assertTrue(opener.requests[2].full_url.endswith("/api/v2/rss/setRule"))
        self.assertTrue(
            opener.requests[3].full_url.endswith("/api/v2/rss/items?withData=false")
        )
        self.assertTrue(opener.requests[4].full_url.endswith("/api/v2/rss/rules"))

    def test_submit_rule_draft_raises_when_read_back_does_not_find_rule(self) -> None:
        from unittest.mock import patch

        feed_url = "https://mikanani.me/RSS/Bangumi?bangumiId=3560&subgroupid=1230"
        opener = _FakeOpener(
            [
                _FakeResponse(""),
                _FakeResponse(""),
                _FakeResponse(json.dumps({"Solo Leveling": {"url": feed_url}})),
                _FakeResponse(json.dumps({})),
            ]
        )

        with patch("mikancli.integrations.qbittorrent.build_opener", return_value=opener):
            with self.assertRaisesRegex(
                QBittorrentError,
                "verification could not find download rule",
            ):
                submit_rule_draft(
                    QBittorrentSettings(url="localhost:8080"),
                    RuleDraft(
                        keyword="Solo Leveling",
                        normalized_keyword="solo leveling",
                        rule_name="Solo Leveling",
                        must_contain=(),
                        must_not_contain=(),
                        feed_url=feed_url,
                    ),
                )


if __name__ == "__main__":
    unittest.main()
