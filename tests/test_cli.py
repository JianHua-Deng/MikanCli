from __future__ import annotations

import argparse
import shutil
import unittest
from pathlib import Path

from mikancli.cli import (
    _build_interactive_draft,
    build_request_from_args,
    resolve_mikan_selection,
)
from mikancli.config import load_config
from mikancli.models import (
    AppConfig,
    MikanBangumi,
    MikanFeedItem,
    MikanSubgroup,
    SearchRequest,
)

TEST_TMP_ROOT = Path(__file__).resolve().parent / ".tmp_cli"


class InteractiveCliTests(unittest.TestCase):
    def setUp(self) -> None:
        TEST_TMP_ROOT.mkdir(exist_ok=True)
        self.temp_dir = TEST_TMP_ROOT / self._testMethodName
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir()

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_build_request_from_flags_skips_prompts_for_json_mode(self) -> None:
        args = argparse.Namespace(
            keyword="Solo Leveling",
            include=["HEVC"],
            exclude=["720p"],
            save_path="D:\\Anime\\Solo Leveling",
            json=True,
        )

        request = build_request_from_args(
            args,
            config=AppConfig(default_save_path="D:\\Anime\\Default"),
            config_path=self.temp_dir / ".mikancli.json",
        )

        self.assertEqual(request.keyword, "Solo Leveling")
        self.assertEqual(request.include_words, ("HEVC",))
        self.assertEqual(request.exclude_words, ("720p",))
        self.assertEqual(request.save_path, "D:\\Anime\\Solo Leveling")

    def test_build_request_requires_keyword_in_json_mode(self) -> None:
        args = argparse.Namespace(
            keyword=None,
            include=[],
            exclude=[],
            save_path=None,
            json=True,
        )

        with self.assertRaisesRegex(ValueError, "keyword is required"):
            build_request_from_args(
                args,
                config=AppConfig(),
                config_path=self.temp_dir / ".mikancli.json",
            )

    def test_build_interactive_draft_asks_include_exclude_after_confirmed_subgroup(self) -> None:
        args = argparse.Namespace(
            keyword="solo leveling",
            include=[],
            exclude=[],
            save_path=None,
            json=False,
        )
        candidates = (
            MikanBangumi(
                bangumi_id=3560,
                title="\u6211\u72ec\u81ea\u5347\u7ea7 \u7b2c\u4e8c\u5b63 -\u8d77\u4e8e\u6697\u5f71-",
                page_url="https://mikanani.me/Home/Bangumi/3560",
                feed_url="https://mikanani.me/RSS/Bangumi?bangumiId=3560",
            ),
        )
        subgroups = (
            MikanSubgroup(
                subgroup_id=1230,
                title="Prejudice-Studio",
                feed_url="https://mikanani.me/RSS/Bangumi?bangumiId=3560&subgroupid=1230",
                publish_group_url="https://mikanani.me/Home/PublishGroup/1003",
            ),
        )
        feed_items = (
            MikanFeedItem(
                title="Episode 01",
                content_length=1024,
                published_at="2025-11-13T19:15:26",
            ),
        )

        from unittest.mock import patch

        config_path = self.temp_dir / ".mikancli.json"
        with patch("mikancli.interactive.search_mikan_bangumi", return_value=candidates), patch(
            "mikancli.interactive.fetch_mikan_subgroups", return_value=subgroups
        ), patch(
            "mikancli.interactive.fetch_mikan_feed_items", return_value=feed_items
        ), patch(
            "mikancli.interactive.select_option",
            side_effect=[0, 0, "yes"],
        ), patch(
            "mikancli.cli.select_option",
            return_value="downloads",
        ), patch(
            "mikancli.cli.prompt_text",
            side_effect=["HEVC", "720p"],
        ), patch(
            "mikancli.cli.get_system_downloads_path", return_value="D:\\Downloads"
        ), patch("mikancli.cli.confirm_choice", return_value=True):
            draft = _build_interactive_draft(
                args,
                config=AppConfig(),
                config_path=config_path,
            )

        self.assertEqual(draft.mikan_subgroup, "Prejudice-Studio")
        self.assertEqual(draft.feed_url, subgroups[0].feed_url)
        self.assertEqual(draft.must_contain, ("Prejudice-Studio", "HEVC"))
        self.assertEqual(draft.must_not_contain, ("720p",))
        self.assertEqual(draft.save_path, "D:\\Downloads")
        self.assertEqual(load_config(config_path).default_save_path, "D:\\Downloads")

    def test_confirm_prompt_places_feed_preview_under_question(self) -> None:
        args = argparse.Namespace(
            keyword="solo leveling",
            include=[],
            exclude=[],
            save_path=None,
            json=False,
        )
        candidates = (
            MikanBangumi(
                bangumi_id=3560,
                title="\u6211\u72ec\u81ea\u5347\u7ea7 \u7b2c\u4e8c\u5b63 -\u8d77\u4e8e\u6697\u5f71-",
                page_url="https://mikanani.me/Home/Bangumi/3560",
                feed_url="https://mikanani.me/RSS/Bangumi?bangumiId=3560",
            ),
        )
        subgroups = (
            MikanSubgroup(
                subgroup_id=1230,
                title="Prejudice-Studio",
                feed_url="https://mikanani.me/RSS/Bangumi?bangumiId=3560&subgroupid=1230",
                publish_group_url="https://mikanani.me/Home/PublishGroup/1003",
            ),
        )
        feed_items = (
            MikanFeedItem(
                title="Episode 01",
                content_length=1024,
                published_at="2025-11-13T19:15:26",
            ),
        )

        captured_messages: list[str] = []

        def fake_select_option(message, options, default=None):
            captured_messages.append(message)
            if message.startswith("Choose the Mikan entry"):
                return 0
            if message.startswith("Choose the subgroup"):
                return 0
            if message.startswith("Use this subgroup feed?"):
                return "yes"
            if message.startswith("Choose a download folder option"):
                return "downloads"
            raise AssertionError(f"Unexpected prompt: {message}")

        from unittest.mock import patch

        config_path = self.temp_dir / ".mikancli.json"
        with patch("mikancli.interactive.search_mikan_bangumi", return_value=candidates), patch(
            "mikancli.interactive.fetch_mikan_subgroups", return_value=subgroups
        ), patch(
            "mikancli.interactive.fetch_mikan_feed_items", return_value=feed_items
        ), patch(
            "mikancli.interactive.select_option", side_effect=fake_select_option
        ), patch(
            "mikancli.cli.select_option", side_effect=fake_select_option
        ), patch(
            "mikancli.cli.prompt_text",
            side_effect=["", ""],
        ), patch(
            "mikancli.cli.get_system_downloads_path", return_value="D:\\Downloads"
        ), patch("mikancli.cli.confirm_choice", return_value=False):
            _build_interactive_draft(
                args,
                config=AppConfig(),
                config_path=config_path,
            )

        confirm_message = next(
            message for message in captured_messages if message.startswith("Use this subgroup feed?")
        )
        self.assertTrue(confirm_message.startswith("Use this subgroup feed?\n\nSubgroup preview:"))
        self.assertIn("1. Episode 01", confirm_message)

    def test_resolve_mikan_selection_uses_first_bangumi_and_subgroup_for_json(self) -> None:
        candidates = (
            MikanBangumi(
                bangumi_id=3530,
                title="\u836f\u5c4b\u5c11\u5973\u7684\u5462\u5583 \u7b2c\u4e8c\u5b63",
                page_url="https://mikanani.me/Home/Bangumi/3530",
                feed_url="https://mikanani.me/RSS/Bangumi?bangumiId=3530",
            ),
            MikanBangumi(
                bangumi_id=3203,
                title="\u836f\u5c4b\u5c11\u5973\u7684\u5462\u5583",
                page_url="https://mikanani.me/Home/Bangumi/3203",
                feed_url="https://mikanani.me/RSS/Bangumi?bangumiId=3203",
            ),
        )
        subgroups = (
            MikanSubgroup(
                subgroup_id=382,
                title="\u55b5\u840c\u5976\u8336\u5c4b",
                feed_url="https://mikanani.me/RSS/Bangumi?bangumiId=3530&subgroupid=382",
                publish_group_url="https://mikanani.me/Home/PublishGroup/246",
            ),
            MikanSubgroup(
                subgroup_id=635,
                title="\u840c\u6a31\u5b57\u5e55\u7ec4",
                feed_url="https://mikanani.me/RSS/Bangumi?bangumiId=3530&subgroupid=635",
                publish_group_url="https://mikanani.me/Home/PublishGroup/411",
            ),
        )

        from unittest.mock import patch

        with patch("mikancli.interactive.search_mikan_bangumi", return_value=candidates), patch(
            "mikancli.interactive.fetch_mikan_subgroups", return_value=subgroups
        ):
            selected_bangumi, selected_subgroup, notes = resolve_mikan_selection(
                SearchRequest(keyword="\u836f\u5c4b\u5c11\u5973\u7684\u5462\u5583"),
            )

        self.assertEqual(selected_bangumi, candidates[0])
        self.assertEqual(selected_subgroup, subgroups[0])
        self.assertEqual(notes, ("qBittorrent submission not implemented yet.",))


if __name__ == "__main__":
    unittest.main()
