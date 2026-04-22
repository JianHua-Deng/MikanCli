from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from mikancli.cli import _prompt_for_save_path, resolve_save_path
from mikancli.config import get_config_path, get_system_downloads_path, load_config
from mikancli.models import AppConfig

TEST_TMP_ROOT = Path(__file__).resolve().parent / ".tmp"


class ConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        TEST_TMP_ROOT.mkdir(exist_ok=True)
        self.temp_dir = TEST_TMP_ROOT / self._testMethodName
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir()

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_load_config_returns_empty_when_file_missing(self) -> None:
        config = load_config(self.temp_dir / ".mikancli.json")
        self.assertIsNone(config.default_save_path)

    def test_get_config_path_uses_base_dir(self) -> None:
        self.assertEqual(
            get_config_path(self.temp_dir),
            self.temp_dir / ".mikancli.json",
        )

    def test_resolve_save_path_uses_cli_value_without_writing_config(self) -> None:
        config_path = self.temp_dir / ".mikancli.json"
        resolved = resolve_save_path(
            "D:\\Anime\\Custom",
            AppConfig(default_save_path="D:\\Anime\\Default"),
            prompt_for_default=False,
            config_path=config_path,
        )

        self.assertEqual(resolved, "D:\\Anime\\Custom")
        self.assertFalse(config_path.exists())

    def test_resolve_save_path_uses_stored_default_without_prompt(self) -> None:
        config_path = self.temp_dir / ".mikancli.json"
        resolved = resolve_save_path(
            None,
            AppConfig(default_save_path="D:\\Anime\\Default"),
            prompt_for_default=False,
            config_path=config_path,
        )

        self.assertEqual(resolved, "D:\\Anime\\Default")

    def test_resolve_save_path_falls_back_to_downloads_without_prompt(self) -> None:
        config_path = self.temp_dir / ".mikancli.json"

        from unittest.mock import patch

        with patch("mikancli.cli.get_system_downloads_path", return_value="D:\\Downloads"):
            resolved = resolve_save_path(
                None,
                AppConfig(),
                prompt_for_default=False,
                config_path=config_path,
            )

        self.assertEqual(resolved, "D:\\Downloads")

    def test_resolve_save_path_uses_interactive_prompt_result(self) -> None:
        config_path = self.temp_dir / ".mikancli.json"

        from unittest.mock import patch

        with patch("mikancli.cli._prompt_for_save_path", return_value="D:\\Anime\\Library"):
            resolved = resolve_save_path(
                None,
                AppConfig(),
                prompt_for_default=True,
                config_path=config_path,
            )

        self.assertEqual(resolved, "D:\\Anime\\Library")

    def test_prompt_for_save_path_can_save_selected_downloads_as_default(self) -> None:
        config_path = self.temp_dir / ".mikancli.json"

        from unittest.mock import patch

        with patch("mikancli.cli.select_option", return_value="downloads"), patch(
            "mikancli.cli.get_system_downloads_path", return_value="D:\\Downloads"
        ), patch("mikancli.cli.confirm_choice", return_value=True):
            resolved = _prompt_for_save_path(
                AppConfig(),
                config_path=config_path,
            )

        self.assertEqual(resolved, "D:\\Downloads")
        self.assertEqual(load_config(config_path).default_save_path, "D:\\Downloads")

    def test_prompt_for_save_path_can_browse_without_saving_default(self) -> None:
        config_path = self.temp_dir / ".mikancli.json"

        from unittest.mock import patch

        with patch("mikancli.cli.select_option", return_value="browse"), patch(
            "mikancli.cli.get_system_downloads_path", return_value="D:\\Downloads"
        ), patch("mikancli.cli.pick_directory", return_value="D:\\Anime\\Picked"), patch(
            "mikancli.cli.confirm_choice", return_value=False
        ):
            resolved = _prompt_for_save_path(
                AppConfig(),
                config_path=config_path,
            )

        self.assertEqual(resolved, "D:\\Anime\\Picked")
        self.assertIsNone(load_config(config_path).default_save_path)

    def test_prompt_for_save_path_uses_saved_default_selection(self) -> None:
        config_path = self.temp_dir / ".mikancli.json"

        from unittest.mock import patch

        with patch("mikancli.cli.select_option", return_value="saved-default"):
            resolved = _prompt_for_save_path(
                AppConfig(default_save_path="D:\\Anime\\Default"),
                config_path=config_path,
            )

        self.assertEqual(resolved, "D:\\Anime\\Default")
        self.assertFalse(config_path.exists())

    def test_load_config_falls_back_to_legacy_autofeedsync_filename(self) -> None:
        legacy_path = self.temp_dir / ".autofeedsync.json"
        legacy_path.write_text(
            '{\n  "default_save_path": "D:\\\\Anime\\\\Legacy"\n}\n',
            encoding="utf-8",
        )

        config = load_config(self.temp_dir / ".mikancli.json")

        self.assertEqual(config.default_save_path, "D:\\Anime\\Legacy")

    def test_get_system_downloads_path_has_nonempty_fallback(self) -> None:
        self.assertTrue(get_system_downloads_path())
