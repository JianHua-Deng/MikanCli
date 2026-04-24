from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from mikancli.cli.save_path_flow import _prompt_for_save_path, resolve_save_path
from mikancli.config import get_config_path, get_system_downloads_path, load_config, save_config
from mikancli.core.models import AppConfig
from mikancli.cli.prompts import ExitRequested

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

    def test_load_config_reads_qbittorrent_fields(self) -> None:
        config_path = self.temp_dir / ".mikancli.json"
        config_path.write_text(
            (
                "{\n"
                '  "default_save_path": "D:\\\\Anime",\n'
                '  "qbittorrent_url": " localhost:8080/ ",\n'
                '  "qbittorrent_username": " admin ",\n'
                '  "qbittorrent_password": "secret"\n'
                "}\n"
            ),
            encoding="utf-8",
        )

        config = load_config(config_path)

        self.assertEqual(config.default_save_path, "D:\\Anime")
        self.assertEqual(config.qbittorrent_url, "localhost:8080/")
        self.assertEqual(config.qbittorrent_username, "admin")
        self.assertEqual(config.qbittorrent_password, "secret")

    def test_save_config_preserves_unknown_keys(self) -> None:
        config_path = self.temp_dir / ".mikancli.json"
        config_path.write_text(
            (
                "{\n"
                '  "default_save_path": "D:\\\\Old",\n'
                '  "extra_key": "keep me"\n'
                "}\n"
            ),
            encoding="utf-8",
        )

        save_config(
            config_path,
            AppConfig(
                default_save_path="D:\\Anime",
                qbittorrent_url="http://localhost:8080",
                qbittorrent_username="admin",
                qbittorrent_password="secret",
            ),
        )

        payload = config_path.read_text(encoding="utf-8")
        self.assertIn('"extra_key": "keep me"', payload)
        config = load_config(config_path)
        self.assertEqual(config.default_save_path, "D:\\Anime")
        self.assertEqual(config.qbittorrent_url, "http://localhost:8080")
        self.assertEqual(config.qbittorrent_username, "admin")
        self.assertEqual(config.qbittorrent_password, "secret")

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

        with patch("mikancli.cli.save_path_flow.get_system_downloads_path", return_value="D:\\Downloads"):
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

        with patch("mikancli.cli.save_path_flow._prompt_for_save_path", return_value="D:\\Anime\\Library"):
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

        with patch("mikancli.cli.save_path_flow.select_option", return_value="downloads"), patch(
            "mikancli.cli.save_path_flow.get_system_downloads_path", return_value="D:\\Downloads"
        ), patch("mikancli.cli.save_path_flow.confirm_choice", return_value=True):
            resolved = _prompt_for_save_path(
                AppConfig(),
                config_path=config_path,
            )

        self.assertEqual(resolved, "D:\\Downloads")
        self.assertEqual(load_config(config_path).default_save_path, "D:\\Downloads")

    def test_prompt_for_save_path_preserves_existing_qbittorrent_fields(self) -> None:
        config_path = self.temp_dir / ".mikancli.json"

        from unittest.mock import patch

        with patch("mikancli.cli.save_path_flow.select_option", return_value="downloads"), patch(
            "mikancli.cli.save_path_flow.get_system_downloads_path", return_value="D:\\Downloads"
        ), patch("mikancli.cli.save_path_flow.confirm_choice", return_value=True):
            _prompt_for_save_path(
                AppConfig(
                    qbittorrent_url="http://localhost:8080",
                    qbittorrent_username="admin",
                    qbittorrent_password="secret",
                ),
                config_path=config_path,
            )

        config = load_config(config_path)
        self.assertEqual(config.default_save_path, "D:\\Downloads")
        self.assertEqual(config.qbittorrent_url, "http://localhost:8080")
        self.assertEqual(config.qbittorrent_username, "admin")
        self.assertEqual(config.qbittorrent_password, "secret")

    def test_prompt_for_save_path_can_browse_without_saving_default(self) -> None:
        config_path = self.temp_dir / ".mikancli.json"

        from unittest.mock import patch

        with patch("mikancli.cli.save_path_flow.select_option", return_value="browse"), patch(
            "mikancli.cli.save_path_flow.get_system_downloads_path", return_value="D:\\Downloads"
        ), patch("mikancli.cli.save_path_flow.pick_directory", return_value="D:\\Anime\\Picked"), patch(
            "mikancli.cli.save_path_flow.confirm_choice", return_value=False
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

        with patch("mikancli.cli.save_path_flow.select_option", return_value="saved-default"):
            resolved = _prompt_for_save_path(
                AppConfig(default_save_path="D:\\Anime\\Default"),
                config_path=config_path,
            )

        self.assertEqual(resolved, "D:\\Anime\\Default")
        self.assertFalse(config_path.exists())

    def test_prompt_for_save_path_can_exit_from_menu(self) -> None:
        config_path = self.temp_dir / ".mikancli.json"

        from unittest.mock import patch

        with patch("mikancli.cli.save_path_flow.select_option", side_effect=ExitRequested):
            with self.assertRaises(ExitRequested):
                _prompt_for_save_path(
                    AppConfig(default_save_path="D:\\Anime\\Default"),
                    config_path=config_path,
                )

    def test_get_system_downloads_path_has_nonempty_fallback(self) -> None:
        self.assertTrue(get_system_downloads_path())
