from __future__ import annotations

import argparse
import shutil
import unittest
from io import StringIO
from pathlib import Path

from mikancli.cli.entrypoint import (
    _build_interactive_draft,
    build_request_from_args,
    main,
    resolve_mikan_selection,
)
from mikancli.cli.search_flow import CONFIRM_SUBGROUP, run_interactive_selection
from mikancli.config import load_config
from mikancli.core.models import (
    AppConfig,
    MikanBangumi,
    MikanFeedItem,
    MikanSubgroup,
    QBittorrentSettings,
    RuleDraft,
    SearchRequest,
)
from mikancli.cli.prompts import ExitRequested
from mikancli.integrations.qbittorrent import QBittorrentError

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
        with patch("mikancli.cli.search_flow.search_mikan_bangumi", return_value=candidates), patch(
            "mikancli.cli.search_flow.fetch_mikan_subgroups", return_value=subgroups
        ), patch(
            "mikancli.cli.search_flow.fetch_mikan_feed_items", return_value=feed_items
        ), patch(
            "mikancli.cli.search_flow.select_option",
            side_effect=[0, 0, CONFIRM_SUBGROUP],
        ), patch(
            "mikancli.cli.save_path_flow.select_option",
            return_value="downloads",
        ), patch(
            "mikancli.cli.input_parsing.prompt_text",
            side_effect=["HEVC", "720p"],
        ), patch(
            "mikancli.cli.save_path_flow.prompt_text",
            side_effect=[""],
        ), patch(
            "mikancli.cli.save_path_flow.get_system_downloads_path", return_value="D:\\Downloads"
        ), patch("mikancli.cli.save_path_flow.confirm_choice", return_value=True), patch(
            "sys.stdout", new=StringIO()
        ):
            draft = _build_interactive_draft(
                args,
                config=AppConfig(),
                config_path=config_path,
            )

        self.assertEqual(draft.mikan_subgroup, "Prejudice-Studio")
        self.assertEqual(draft.feed_url, subgroups[0].feed_url)
        self.assertEqual(draft.must_contain, ("HEVC",))
        self.assertEqual(draft.must_not_contain, ("720p",))
        self.assertEqual(
            draft.save_path,
            "D:\\Downloads\\\u6211\u72ec\u81ea\u5347\u7ea7 \u7b2c\u4e8c\u5b63 -\u8d77\u4e8e\u6697\u5f71-",
        )
        self.assertEqual(load_config(config_path).default_save_path, "D:\\Downloads")

    def test_build_interactive_draft_allows_custom_content_folder_name(self) -> None:
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

        with patch("mikancli.cli.search_flow.search_mikan_bangumi", return_value=candidates), patch(
            "mikancli.cli.search_flow.fetch_mikan_subgroups", return_value=subgroups
        ), patch(
            "mikancli.cli.search_flow.fetch_mikan_feed_items", return_value=feed_items
        ), patch(
            "mikancli.cli.search_flow.select_option",
            side_effect=[0, 0, CONFIRM_SUBGROUP],
        ), patch(
            "mikancli.cli.save_path_flow.select_option",
            return_value="downloads",
        ), patch(
            "mikancli.cli.input_parsing.prompt_text",
            side_effect=["", ""],
        ), patch(
            "mikancli.cli.save_path_flow.prompt_text",
            side_effect=["Solo Leveling S2"],
        ), patch(
            "mikancli.cli.save_path_flow.get_system_downloads_path", return_value="D:\\Downloads"
        ), patch("mikancli.cli.save_path_flow.confirm_choice", return_value=False), patch(
            "sys.stdout", new=StringIO()
        ):
            draft = _build_interactive_draft(
                args,
                config=AppConfig(),
                config_path=self.temp_dir / ".mikancli.json",
            )

        self.assertEqual(draft.save_path, "D:\\Downloads\\Solo Leveling S2")

    def test_confirm_prompt_places_yes_option_next_to_question_after_feed_preview(self) -> None:
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

        def fake_select_option(
            message,
            options,
            default=None,
            allow_exit=False,
            separator_before_values=(),
            separator_before_exit=True,
        ):
            captured_messages.append(message)
            if message.startswith("Choose the Mikan entry"):
                return 0
            if message.startswith("Choose the subgroup"):
                return 0
            if message.startswith("Use this subgroup feed?"):
                return CONFIRM_SUBGROUP
            if message.startswith("Choose a download folder option"):
                return "downloads"
            raise AssertionError(f"Unexpected prompt: {message}")

        from unittest.mock import patch

        config_path = self.temp_dir / ".mikancli.json"
        stdout = StringIO()

        with patch("mikancli.cli.search_flow.search_mikan_bangumi", return_value=candidates), patch(
            "mikancli.cli.search_flow.fetch_mikan_subgroups", return_value=subgroups
        ), patch(
            "mikancli.cli.search_flow.fetch_mikan_feed_items", return_value=feed_items
        ), patch(
            "mikancli.cli.search_flow.select_option", side_effect=fake_select_option
        ), patch(
            "mikancli.cli.save_path_flow.select_option", side_effect=fake_select_option
        ), patch(
            "mikancli.cli.input_parsing.prompt_text",
            side_effect=["", ""],
        ), patch(
            "mikancli.cli.save_path_flow.prompt_text",
            side_effect=[""],
        ), patch(
            "mikancli.cli.save_path_flow.get_system_downloads_path", return_value="D:\\Downloads"
        ), patch("mikancli.cli.save_path_flow.confirm_choice", return_value=False), patch(
            "sys.stdout", new=stdout
        ):
            _build_interactive_draft(
                args,
                config=AppConfig(),
                config_path=config_path,
            )

        confirm_message = next(
            message for message in captured_messages if message.startswith("Use this subgroup feed?")
        )
        self.assertEqual(confirm_message, "Use this subgroup feed?")
        self.assertIn("Subgroup preview:", stdout.getvalue())
        self.assertIn("1. Episode 01", stdout.getvalue())

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

        with patch("mikancli.cli.search_flow.search_mikan_bangumi", return_value=candidates), patch(
            "mikancli.cli.search_flow.fetch_mikan_subgroups", return_value=subgroups
        ):
            selected_bangumi, selected_subgroup, notes = resolve_mikan_selection(
                SearchRequest(keyword="\u836f\u5c4b\u5c11\u5973\u7684\u5462\u5583"),
            )

        self.assertEqual(selected_bangumi, candidates[0])
        self.assertEqual(selected_subgroup, subgroups[0])
        self.assertEqual(
            notes,
            ("JSON mode only prints the draft; interactive mode can submit it to qBittorrent.",),
        )

    def test_main_exits_cleanly_when_user_chooses_exit(self) -> None:
        from unittest.mock import patch

        stdout = StringIO()

        with patch("mikancli.cli.entrypoint.ensure_runtime_dependencies"), patch(
            "mikancli.cli.entrypoint.get_config_path", return_value=self.temp_dir / ".mikancli.json"
        ), patch("mikancli.cli.entrypoint.load_config", return_value=AppConfig()), patch(
            "mikancli.cli.entrypoint.select_option", side_effect=ExitRequested
        ), patch("sys.stdout", new=stdout):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        self.assertIn("Exited MikanCli.", stdout.getvalue())

    def test_main_setup_qbittorrent_defaults_to_localhost_and_saves_on_success(self) -> None:
        from unittest.mock import patch

        config_path = self.temp_dir / ".mikancli.json"
        stdout = StringIO()

        def fake_check_connection(settings: QBittorrentSettings) -> str:
            self.assertEqual(settings.url, "http://localhost:8080")
            self.assertIsNone(settings.username)
            self.assertIsNone(settings.password)
            return "5.0.0"

        with patch("mikancli.cli.entrypoint.ensure_runtime_dependencies"), patch(
            "mikancli.cli.entrypoint.get_config_path", return_value=config_path
        ), patch("mikancli.cli.entrypoint.load_config", return_value=AppConfig()), patch(
            "mikancli.cli.qbittorrent_flow.prompt_text",
            side_effect=["", ""],
        ), patch(
            "mikancli.cli.qbittorrent_flow.prompt_password",
            return_value="",
        ), patch(
            "mikancli.cli.qbittorrent_flow.check_connection",
            side_effect=fake_check_connection,
        ), patch("sys.stdout", new=stdout):
            exit_code = main(["--setup-qbittorrent"])

        self.assertEqual(exit_code, 0)
        saved_config = load_config(config_path)
        self.assertEqual(saved_config.qbittorrent_url, "http://localhost:8080")
        self.assertIsNone(saved_config.qbittorrent_username)
        self.assertIsNone(saved_config.qbittorrent_password)
        self.assertIn("qBittorrent connection verified successfully", stdout.getvalue())

    def test_main_setup_qbittorrent_does_not_save_on_failed_verification(self) -> None:
        from unittest.mock import patch

        config_path = self.temp_dir / ".mikancli.json"
        stdout = StringIO()

        with patch("mikancli.cli.entrypoint.ensure_runtime_dependencies"), patch(
            "mikancli.cli.entrypoint.get_config_path", return_value=config_path
        ), patch("mikancli.cli.entrypoint.load_config", return_value=AppConfig()), patch(
            "mikancli.cli.qbittorrent_flow.prompt_text",
            side_effect=["localhost:9090", "admin"],
        ), patch(
            "mikancli.cli.qbittorrent_flow.prompt_password",
            return_value="wrong",
        ), patch(
            "mikancli.cli.qbittorrent_flow.check_connection",
            side_effect=QBittorrentError("bad credentials"),
        ), patch("sys.stdout", new=stdout):
            exit_code = main(["--setup-qbittorrent"])

        self.assertEqual(exit_code, 1)
        self.assertFalse(config_path.exists())
        self.assertIn("bad credentials", stdout.getvalue())

    def test_main_shows_startup_menu_and_search_route_can_continue_without_qbittorrent_setup(self) -> None:
        from unittest.mock import patch

        draft = object()

        with patch("mikancli.cli.entrypoint.ensure_runtime_dependencies"), patch(
            "mikancli.cli.entrypoint.get_config_path", return_value=self.temp_dir / ".mikancli.json"
        ), patch("mikancli.cli.entrypoint.select_option", return_value="search") as select_mock, patch(
            "mikancli.cli.entrypoint.load_config", return_value=AppConfig()
        ), patch(
            "mikancli.cli.qbittorrent_flow.confirm_choice",
            return_value=False,
        ) as confirm_mock, patch(
            "mikancli.cli.entrypoint._build_interactive_draft",
            return_value=draft,
        ) as build_mock, patch(
            "mikancli.cli.entrypoint.print_text_summary",
            return_value=0,
        ):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        select_mock.assert_called_once_with(
            "Choose what you want to do",
            [
                ("search", "Search anime"),
                ("qbittorrent", "Modify qBittorrent configurations"),
            ],
            default="search",
            allow_exit=True,
        )
        confirm_mock.assert_called_once_with(
            "qBittorrent is not set up yet. Set up qBittorrent WebUI now?",
            default=True,
            allow_exit=True,
        )
        build_mock.assert_called_once()

    def test_main_returns_to_startup_menu_after_qbittorrent_configuration_route(self) -> None:
        from unittest.mock import patch

        stdout = StringIO()

        with patch("mikancli.cli.entrypoint.ensure_runtime_dependencies"), patch(
            "mikancli.cli.entrypoint.get_config_path", return_value=self.temp_dir / ".mikancli.json"
        ), patch(
            "mikancli.cli.entrypoint.select_option",
            side_effect=["qbittorrent", ExitRequested],
        ) as select_mock, patch(
            "mikancli.cli.entrypoint.load_config", return_value=AppConfig()
        ), patch(
            "mikancli.cli.entrypoint.run_qbittorrent_configuration_flow",
            return_value=0,
        ) as route_mock, patch(
            "mikancli.cli.entrypoint._build_interactive_draft",
        ) as build_mock, patch("sys.stdout", new=stdout):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        route_mock.assert_called_once()
        self.assertEqual(select_mock.call_count, 2)
        build_mock.assert_not_called()
        self.assertIn("Exited MikanCli.", stdout.getvalue())

    def test_main_search_route_can_launch_qbittorrent_setup_from_interactive_start(self) -> None:
        from unittest.mock import patch

        draft = object()

        with patch("mikancli.cli.entrypoint.ensure_runtime_dependencies"), patch(
            "mikancli.cli.entrypoint.get_config_path", return_value=self.temp_dir / ".mikancli.json"
        ), patch("mikancli.cli.entrypoint.select_option", return_value="search"), patch(
            "mikancli.cli.entrypoint.load_config", return_value=AppConfig()
        ), patch(
            "mikancli.cli.qbittorrent_flow.confirm_choice",
            return_value=True,
        ), patch(
            "mikancli.cli.qbittorrent_flow.setup_qbittorrent",
            return_value=0,
        ) as setup_mock, patch(
            "mikancli.cli.entrypoint._build_interactive_draft",
            return_value=draft,
        ) as build_mock, patch(
            "mikancli.cli.entrypoint.print_text_summary",
            return_value=0,
        ):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        setup_mock.assert_called_once()
        build_mock.assert_called_once()

    def test_main_search_route_can_submit_confirmed_draft_to_qbittorrent(self) -> None:
        from unittest.mock import patch

        draft = RuleDraft(
            keyword="Solo Leveling",
            normalized_keyword="solo leveling",
            rule_name="Solo Leveling",
            must_contain=("HEVC",),
            must_not_contain=("720p",),
            feed_url="https://mikanani.me/RSS/Bangumi?bangumiId=3560&subgroupid=1230",
            save_path="D:\\Anime\\Solo Leveling",
        )
        config = AppConfig(
            qbittorrent_url="http://localhost:8080",
            qbittorrent_username="admin",
            qbittorrent_password="secret",
            qbittorrent_category="Anime",
            qbittorrent_add_paused=True,
        )

        with patch("mikancli.cli.entrypoint.ensure_runtime_dependencies"), patch(
            "mikancli.cli.entrypoint.get_config_path", return_value=self.temp_dir / ".mikancli.json"
        ), patch("mikancli.cli.entrypoint.select_option", return_value="search"), patch(
            "mikancli.cli.entrypoint.load_config", return_value=config
        ), patch(
            "mikancli.cli.entrypoint._build_interactive_draft",
            return_value=draft,
        ), patch(
            "mikancli.cli.entrypoint.print_text_summary",
            return_value=0,
        ), patch(
            "mikancli.cli.qbittorrent_flow.confirm_choice",
            return_value=True,
        ), patch(
            "mikancli.cli.qbittorrent_flow.submit_rule_draft",
        ) as submit_mock, patch("sys.stdout", new=StringIO()):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        submit_mock.assert_called_once_with(
            QBittorrentSettings(
                url="http://localhost:8080",
                username="admin",
                password="secret",
            ),
            draft,
            add_paused=True,
            assigned_category="Anime",
        )

    def test_main_search_route_can_skip_qbittorrent_submission(self) -> None:
        from unittest.mock import patch

        draft = RuleDraft(
            keyword="Solo Leveling",
            normalized_keyword="solo leveling",
            rule_name="Solo Leveling",
            must_contain=(),
            must_not_contain=(),
            feed_url="https://mikanani.me/RSS/Bangumi?bangumiId=3560&subgroupid=1230",
        )
        stdout = StringIO()

        with patch("mikancli.cli.entrypoint.ensure_runtime_dependencies"), patch(
            "mikancli.cli.entrypoint.get_config_path", return_value=self.temp_dir / ".mikancli.json"
        ), patch(
            "mikancli.cli.entrypoint.select_option",
            side_effect=["search", ExitRequested],
        ) as select_mock, patch(
            "mikancli.cli.entrypoint.load_config",
            return_value=AppConfig(qbittorrent_url="http://localhost:8080"),
        ), patch(
            "mikancli.cli.entrypoint._build_interactive_draft",
            return_value=draft,
        ), patch(
            "mikancli.cli.entrypoint.print_text_summary",
            return_value=0,
        ), patch(
            "mikancli.cli.qbittorrent_flow.confirm_choice",
            return_value=False,
        ), patch(
            "mikancli.cli.qbittorrent_flow.submit_rule_draft",
        ) as submit_mock, patch("sys.stdout", new=stdout):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(select_mock.call_count, 2)
        self.assertIn("Exited MikanCli.", stdout.getvalue())
        submit_mock.assert_not_called()

    def test_main_exits_cleanly_from_qbittorrent_submission_prompt(self) -> None:
        from unittest.mock import patch

        draft = RuleDraft(
            keyword="Solo Leveling",
            normalized_keyword="solo leveling",
            rule_name="Solo Leveling",
            must_contain=(),
            must_not_contain=(),
            feed_url="https://mikanani.me/RSS/Bangumi?bangumiId=3560&subgroupid=1230",
        )
        stdout = StringIO()

        with patch("mikancli.cli.entrypoint.ensure_runtime_dependencies"), patch(
            "mikancli.cli.entrypoint.get_config_path", return_value=self.temp_dir / ".mikancli.json"
        ), patch("mikancli.cli.entrypoint.select_option", return_value="search"), patch(
            "mikancli.cli.entrypoint.load_config",
            return_value=AppConfig(qbittorrent_url="http://localhost:8080"),
        ), patch(
            "mikancli.cli.entrypoint._build_interactive_draft",
            return_value=draft,
        ), patch(
            "mikancli.cli.entrypoint.print_text_summary",
            return_value=0,
        ), patch(
            "mikancli.cli.qbittorrent_flow.confirm_choice",
            side_effect=ExitRequested,
        ), patch(
            "mikancli.cli.qbittorrent_flow.submit_rule_draft",
        ) as submit_mock, patch("sys.stdout", new=stdout):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        self.assertIn("Exited MikanCli.", stdout.getvalue())
        submit_mock.assert_not_called()

    def test_main_retries_qbittorrent_setup_after_failed_attempt_when_user_does_not_skip(self) -> None:
        from unittest.mock import patch

        draft = object()

        with patch("mikancli.cli.entrypoint.ensure_runtime_dependencies"), patch(
            "mikancli.cli.entrypoint.get_config_path", return_value=self.temp_dir / ".mikancli.json"
        ), patch("mikancli.cli.entrypoint.select_option", return_value="search"), patch(
            "mikancli.cli.entrypoint.load_config", return_value=AppConfig()
        ), patch(
            "mikancli.cli.qbittorrent_flow.confirm_choice",
            side_effect=[True, False],
        ) as confirm_mock, patch(
            "mikancli.cli.qbittorrent_flow.setup_qbittorrent",
            side_effect=[1, 0],
        ) as setup_mock, patch(
            "mikancli.cli.entrypoint._build_interactive_draft",
            return_value=draft,
        ) as build_mock, patch(
            "mikancli.cli.entrypoint.print_text_summary",
            return_value=0,
        ):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(setup_mock.call_count, 2)
        self.assertEqual(confirm_mock.call_count, 2)
        build_mock.assert_called_once()

    def test_qbittorrent_configuration_route_retries_after_failed_setup_when_user_chooses_retry(self) -> None:
        from unittest.mock import patch

        stdout = StringIO()

        with patch("mikancli.cli.entrypoint.ensure_runtime_dependencies"), patch(
            "mikancli.cli.entrypoint.get_config_path", return_value=self.temp_dir / ".mikancli.json"
        ), patch(
            "mikancli.cli.entrypoint.select_option",
            side_effect=["qbittorrent", ExitRequested],
        ), patch(
            "mikancli.cli.entrypoint.load_config", return_value=AppConfig()
        ), patch(
            "mikancli.cli.qbittorrent_flow.confirm_choice",
            return_value=True,
        ), patch(
            "mikancli.cli.qbittorrent_flow.setup_qbittorrent",
            side_effect=[1, 0],
        ) as setup_mock, patch(
            "mikancli.cli.entrypoint._build_interactive_draft",
        ) as build_mock, patch("sys.stdout", new=stdout):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(setup_mock.call_count, 2)
        build_mock.assert_not_called()
        self.assertIn("Exited MikanCli.", stdout.getvalue())

    def test_qbittorrent_configuration_route_returns_to_startup_when_user_stops_retrying(self) -> None:
        from unittest.mock import patch

        stdout = StringIO()

        with patch("mikancli.cli.entrypoint.ensure_runtime_dependencies"), patch(
            "mikancli.cli.entrypoint.get_config_path", return_value=self.temp_dir / ".mikancli.json"
        ), patch(
            "mikancli.cli.entrypoint.select_option",
            side_effect=["qbittorrent", ExitRequested],
        ) as select_mock, patch(
            "mikancli.cli.entrypoint.load_config", return_value=AppConfig()
        ), patch(
            "mikancli.cli.qbittorrent_flow.confirm_choice",
            return_value=False,
        ), patch(
            "mikancli.cli.qbittorrent_flow.setup_qbittorrent",
            return_value=1,
        ), patch("sys.stdout", new=stdout):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(select_mock.call_count, 2)
        self.assertIn("Exited MikanCli.", stdout.getvalue())

    def test_initial_search_prompt_mentions_exit(self) -> None:
        from unittest.mock import patch

        with patch(
            "mikancli.cli.search_flow.prompt_required_text",
            side_effect=ExitRequested,
        ) as prompt_mock:
            with self.assertRaises(ExitRequested):
                run_interactive_selection(initial_keyword=None)

        prompt_mock.assert_called_once_with(
            "Enter anime title or search keyword (or type 'exit' to quit): "
        )


if __name__ == "__main__":
    unittest.main()
