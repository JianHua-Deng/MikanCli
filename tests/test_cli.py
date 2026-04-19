from __future__ import annotations

import argparse
import shutil
import unittest
from pathlib import Path

from autofeedsync.cli import build_request_from_args
from autofeedsync.config import load_config
from autofeedsync.models import AppConfig

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

    def test_build_request_from_flags_skips_interactive_prompts(self) -> None:
        args = argparse.Namespace(
            keyword="Solo Leveling",
            include=["HEVC"],
            exclude=["720p"],
            group="SubsPlease",
            resolution="1080p",
            save_path="D:\\Anime\\Solo Leveling",
            json=False,
        )

        request = build_request_from_args(
            args,
            config=AppConfig(default_save_path="D:\\Anime\\Default"),
            config_path=self.temp_dir / ".autofeedsync.json",
        )

        self.assertEqual(request.keyword, "Solo Leveling")
        self.assertEqual(request.include_words, ("HEVC",))
        self.assertEqual(request.exclude_words, ("720p",))
        self.assertEqual(request.group, "SubsPlease")
        self.assertEqual(request.resolution, "1080p")
        self.assertEqual(request.save_path, "D:\\Anime\\Solo Leveling")

    def test_build_request_from_interactive_prompts(self) -> None:
        args = argparse.Namespace(
            keyword=None,
            include=[],
            exclude=[],
            group=None,
            resolution=None,
            save_path=None,
            json=False,
        )

        from unittest.mock import patch

        config_path = self.temp_dir / ".autofeedsync.json"
        with patch(
            "autofeedsync.cli.prompt_text",
            side_effect=[
                "\u836f\u5c4b\u5c11\u5973\u7684\u5462\u55c3",
                "\u55b5\u840c\u5976\u8336\u5c4b",
                "HEVC, \u7b80\u7e41\u5185\u5c01",
                "720p",
            ],
        ), patch(
            "autofeedsync.cli.select_option", side_effect=["1080p", "downloads"]
        ), patch(
            "autofeedsync.cli.get_system_downloads_path", return_value="D:\\Downloads"
        ), patch("autofeedsync.cli.confirm_choice", return_value=True):
            request = build_request_from_args(
                args,
                config=AppConfig(),
                config_path=config_path,
            )

        self.assertEqual(request.keyword, "\u836f\u5c4b\u5c11\u5973\u7684\u5462\u55c3")
        self.assertEqual(request.group, "\u55b5\u840c\u5976\u8336\u5c4b")
        self.assertEqual(request.resolution, "1080p")
        self.assertEqual(request.include_words, ("HEVC", "\u7b80\u7e41\u5185\u5c01"))
        self.assertEqual(request.exclude_words, ("720p",))
        self.assertEqual(request.save_path, "D:\\Downloads")
        self.assertEqual(load_config(config_path).default_save_path, "D:\\Downloads")

    def test_build_request_requires_keyword_in_json_mode(self) -> None:
        args = argparse.Namespace(
            keyword=None,
            include=[],
            exclude=[],
            group=None,
            resolution=None,
            save_path=None,
            json=True,
        )

        with self.assertRaisesRegex(ValueError, "keyword is required"):
            build_request_from_args(
                args,
                config=AppConfig(),
                config_path=self.temp_dir / ".autofeedsync.json",
            )
