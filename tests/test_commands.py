from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from mikancli.cli import commands, entrypoint, search_flow
from mikancli.core.models import AppConfig, MikanBangumi, MikanFeedItem, MikanSubgroup
from mikancli.integrations.mikan import MikanLookupError


FEED = "https://mikanani.me/RSS/Bangumi?bangumiId=123&subgroupid=456"
GROUP = MikanSubgroup(456, "Chosen subgroup", FEED)
CONFIG = AppConfig(qbittorrent_url="http://localhost:8080", qbittorrent_add_paused=True)


class MemoryClient:
    """A stateful external-system stand-in for the full CLI plan/apply workflow."""

    def __init__(self):
        self.rules = {}
        self.feeds = {}
        self.writes = 0

    def login(self):
        pass

    def get_auto_downloading_rules(self):
        return copy.deepcopy(self.rules)

    def get_rss_items(self):
        return copy.deepcopy(self.feeds)

    def add_feed(self, url, *, path):
        self.feeds[path] = {"url": url}
        self.writes += 1

    def set_auto_downloading_rule(self, name, definition):
        self.rules[name] = copy.deepcopy(definition)
        self.writes += 1


class CommandTests(TestCase):
    def invoke(self, argv, *, stdin=""):
        out, err = StringIO(), StringIO()
        with (
            patch("sys.stdin", StringIO(stdin)),
            redirect_stdout(out), redirect_stderr(err),
        ):
            code = entrypoint.main(argv)
        self.assertEqual(err.getvalue(), "", err.getvalue())
        result = json.loads(out.getvalue())
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["ok"], code == 0)
        self.assertEqual(set(result), {"schema_version", "ok", "data", "error"})
        return code, result

    def isolated_config(self, config=CONFIG):
        return patch.object(commands, "load_command_config", return_value=(Path("isolated.json"), config))

    def test_discovery_returns_choices_without_selecting_and_paginates(self):
        candidates = tuple(MikanBangumi(i, f"Anime {i}", f"https://example.test/{i}", FEED) for i in range(1, 4))
        with self.isolated_config(), patch.object(commands, "search_mikan_bangumi", return_value=candidates) as search:
            code, result = self.invoke(["--timeout", "8", "search", "anime", "--offset", "1", "--limit", "1", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(result["data"]["total"], 3)
        self.assertEqual([item["bangumi_id"] for item in result["data"]["items"]], [2])
        search.assert_called_once_with("anime", timeout=8)

    def test_empty_search_is_successful(self):
        with self.isolated_config(), patch.object(commands, "search_mikan_bangumi", return_value=()):
            code, result = self.invoke(["search", "no match"])
        self.assertEqual(code, 0)
        self.assertEqual(result["data"]["items"], [])

    def test_subgroups_and_feed_honor_explicit_selection(self):
        with self.isolated_config(), patch.object(commands, "fetch_mikan_subgroups", return_value=(GROUP,)):
            _, groups = self.invoke(["subgroups", "--bangumi-id", "123"])
            with patch.object(commands, "fetch_mikan_feed_items", return_value=(MikanFeedItem("Episode 1"), MikanFeedItem("Episode 2"))):
                code, feed = self.invoke(["feed", "--bangumi-id", "123", "--subgroup-id", "456", "--offset", "1"])
            with patch.object(commands, "fetch_mikan_feed_items") as fetch:
                missing_code, missing = self.invoke(["feed", "--bangumi-id", "123", "--subgroup-id", "999"])
        self.assertEqual(groups["data"]["items"][0]["subgroup_id"], 456)
        self.assertEqual(code, 0)
        self.assertEqual(feed["data"]["items"][0]["title"], "Episode 2")
        self.assertEqual(missing_code, 3)
        self.assertEqual(missing["error"]["code"], "NOT_FOUND")
        fetch.assert_not_called()

    def test_plan_file_apply_repeat_inspect_and_conflict(self):
        client = MemoryClient()
        with (
            self.isolated_config(),
            patch("mikancli.services.rules.fetch_mikan_subgroups", return_value=(GROUP,)),
            patch("mikancli.services.rules.QBittorrentClient", return_value=client),
        ):
            code, plan = self.invoke(["rules", "plan", "--bangumi-id", "123", "--subgroup-id", "456", "--name", "One Piece", "--include", "1080p", "--save-path", "D:/Anime/One Piece"])
            self.assertEqual(code, 0)
            self.assertEqual(client.writes, 0)
            self.assertTrue(plan["data"]["rule_definition"]["addPaused"])
            with tempfile.TemporaryDirectory(prefix=".tmp_commands_", dir=Path(__file__).resolve().parents[1]) as directory:
                saved = Path(directory) / "plan.json"
                saved.write_text(json.dumps(plan), encoding="utf-8-sig")
                code, applied = self.invoke(["rules", "apply", "--file", str(saved)])
            self.assertEqual(code, 0)
            self.assertEqual(applied["data"]["status"], "created")
            writes = client.writes
            code, repeated = self.invoke(["rules", "apply", "--file", "-"], stdin=json.dumps(plan["data"]))
            self.assertEqual(code, 0)
            self.assertEqual(repeated["data"]["status"], "unchanged")
            self.assertEqual(client.writes, writes)
            _, inspected = self.invoke(["rules", "get", "--name", "One Piece"])
            self.assertEqual(inspected["data"]["rule_definition"]["savePath"], "D:/Anime/One Piece")
            changed = copy.deepcopy(plan)
            changed["data"]["rule_definition"]["savePath"] = "D:/Other"
            code, conflict = self.invoke(["rules", "apply", "--file", "-"], stdin=json.dumps(changed))
            self.assertEqual(code, 4)
            self.assertEqual(conflict["error"]["code"], "CONFLICT")
            self.assertEqual(client.writes, writes)
            code, updated = self.invoke(["rules", "apply", "--file", "-", "--if-exists", "replace"], stdin=json.dumps(changed))
            self.assertEqual(code, 0)
            self.assertEqual(updated["data"]["status"], "updated")

    def test_plan_overrides_can_clear_saved_path_and_paused_state(self):
        with self.isolated_config(AppConfig(default_save_path="D:/Saved", qbittorrent_add_paused=True)), patch("mikancli.services.rules.fetch_mikan_subgroups", return_value=(GROUP,)):
            code, result = self.invoke(["rules", "plan", "--bangumi-id", "123", "--subgroup-id", "456", "--name", "One Piece", "--save-path", "", "--no-add-paused"])
        self.assertEqual(code, 0)
        self.assertEqual(result["data"]["rule_definition"]["savePath"], "")
        self.assertFalse(result["data"]["rule_definition"]["addPaused"])

    def test_invalid_arguments_are_json_errors_without_prompts(self):
        invalid = [
            ["search"], ["search", "  "], ["rules"], ["rules", "plan"],
            ["rules", "get", "--name", "x", "--unknown"],
            ["feed", "--bangumi-id", "0", "--subgroup-id", "1"],
            ["search", "x", "--limit", "-1"],
            ["search", "x", "--timeout", "nan"],
            ["search", "x", "--timeout", "inf"],
            ["search", "x", "--timeout", "301"],
            ["search", "x", "--language", "invalid"],
        ]
        with patch.object(entrypoint, "prompt_startup_action", side_effect=AssertionError("prompted")):
            for argv in invalid:
                with self.subTest(argv=argv):
                    code, result = self.invoke(argv)
                    self.assertEqual(code, 2)
                    self.assertEqual(result["error"]["code"], "INVALID_ARGUMENT")

    def test_common_options_work_at_every_command_level(self):
        for argv in (
            ["--config", "test.json", "--timeout", "7", "rules", "get", "--name", "x"],
            ["rules", "--config", "test.json", "--timeout", "7", "get", "--name", "x"],
            ["rules", "get", "--name", "x", "--config", "test.json", "--timeout", "7"],
        ):
            with self.subTest(argv=argv):
                args = commands.build_command_parser().parse_args(argv)
                self.assertEqual(args.config, "test.json")
                self.assertEqual(args.timeout, 7)

    def test_invalid_plan_or_failed_envelope_never_connects(self):
        for content in ("not json", "[]", "{}", '{"schema_version":1,"ok":false,"data":null,"error":{}}', '{"schema_version":true,"ok":true,"data":{},"error":null}'):
            with self.subTest(content=content), self.isolated_config(), patch("mikancli.services.rules.QBittorrentClient") as client:
                code, _ = self.invoke(["rules", "apply", "--file", "-"], stdin=content)
                self.assertEqual(code, 2)
                client.assert_not_called()

    def test_missing_plan_file_is_actionable_error(self):
        with self.isolated_config():
            code, result = self.invoke(["rules", "apply", "--file", "nonexistent-plan-file.json"])
        self.assertEqual(code, 2)
        self.assertEqual(result["error"]["code"], "INVALID_ARGUMENT")

    def test_upstream_failure_and_cancellation_have_machine_readable_results(self):
        for failure, code, expected in ((MikanLookupError("Unavailable", code="NETWORK_ERROR", retryable=True), 1, "NETWORK_ERROR"), (KeyboardInterrupt(), 130, "CANCELLED")):
            with self.subTest(expected=expected), self.isolated_config(), patch.object(commands, "search_mikan_bangumi", side_effect=failure):
                actual_code, result = self.invoke(["search", "x"])
            self.assertEqual(actual_code, code)
            self.assertEqual(result["error"]["code"], expected)

    def test_offline_schema_requires_neither_config_nor_network(self):
        with patch.object(commands, "load_command_config", side_effect=AssertionError("read config")):
            code, result = self.invoke(["schema"])
        self.assertEqual(code, 0)
        self.assertIn("rule_definition", result["data"]["plan"]["properties"])

    def test_absent_qbittorrent_config_fails_without_setup_prompt(self):
        with self.isolated_config(AppConfig()), patch.object(entrypoint, "setup_qbittorrent", side_effect=AssertionError("setup")):
            code, result = self.invoke(["rules", "get", "--name", "x"])
        self.assertEqual(code, 3)
        self.assertEqual(result["error"]["code"], "NOT_CONFIGURED")

    def test_environment_precedence_bom_config_and_redaction(self):
        with tempfile.TemporaryDirectory(prefix=".tmp_commands_", dir=Path(__file__).resolve().parents[1]) as directory:
            env_path = Path(directory) / "environment.json"
            explicit_path = Path(directory) / "explicit.json"
            env_path.write_text(json.dumps({"qbittorrent_url": "http://localhost:8080", "default_save_path": "D:/Environment"}), encoding="utf-8-sig")
            explicit_path.write_text(json.dumps({"default_save_path": "D:/Explicit", "qbittorrent_password": "saved-secret"}), encoding="utf-8")
            env = {"MIKANCLI_CONFIG": str(env_path), "MIKANCLI_QBITTORRENT_USERNAME": "secret-user", "MIKANCLI_QBITTORRENT_PASSWORD": "secret-password"}
            with patch.dict(os.environ, env, clear=True):
                _, result = self.invoke(["config", "show"])
                self.assertEqual(result["data"]["settings"]["default_save_path"], "D:/Environment")
                self.assertEqual(result["data"]["settings"]["qbittorrent_url"], "http://localhost:8080")
                self.assertNotIn("secret-", json.dumps(result))
                _, explicit = self.invoke(["config", "show", "--config", str(explicit_path)])
                self.assertEqual(explicit["data"]["settings"]["default_save_path"], "D:/Explicit")
                self.assertNotIn("saved-secret", json.dumps(explicit))

    def test_missing_config_is_empty_and_corrupt_config_is_error(self):
        with tempfile.TemporaryDirectory(prefix=".tmp_commands_", dir=Path(__file__).resolve().parents[1]) as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / "new.json"
            code, result = self.invoke(["config", "show", "--config", str(path)])
            self.assertEqual(code, 0)
            self.assertIsNone(result["data"]["settings"]["qbittorrent_url"])
            self.assertFalse(path.exists())
            path.write_text("{broken", encoding="utf-8")
            code, result = self.invoke(["config", "show", "--config", str(path)])
            self.assertEqual(code, 2)
            self.assertEqual(result["error"]["code"], "INVALID_CONFIG")

    def test_config_url_redaction_and_invalid_base_urls(self):
        with self.isolated_config(AppConfig(qbittorrent_url="http://private-user:private-password@localhost:8080/base?token=secret#secret")):
            _, shown = self.invoke(["config", "show"])
        self.assertEqual(shown["data"]["settings"]["qbittorrent_url"], "http://localhost:8080/base")
        for url in ("http://localhost?route=x", "http://localhost#fragment", "http://localhost:notaport", "http://@localhost", "file:///tmp/qbittorrent"):
            with self.subTest(url=url), self.isolated_config(AppConfig(qbittorrent_url=url)):
                code, result = self.invoke(["rules", "get", "--name", "x"])
                self.assertEqual(code, 2)
                self.assertEqual(result["error"]["code"], "INVALID_CONFIG")

    def test_legacy_draft_refuses_ambiguous_or_failed_lookup(self):
        candidates = (MikanBangumi(1, "First", "https://example.test/1", FEED), MikanBangumi(2, "Second", "https://example.test/2", FEED))
        for outcome, code, error in ((candidates, 4, "AMBIGUOUS_SELECTION"), ((), 3, "NOT_FOUND"), (MikanLookupError("Unavailable", code="NETWORK_ERROR", retryable=True), 1, "NETWORK_ERROR")):
            with self.subTest(error=error), patch.object(entrypoint, "load_config", return_value=AppConfig()), patch.object(search_flow, "search_mikan_bangumi", **({"side_effect": outcome} if isinstance(outcome, Exception) else {"return_value": outcome})):
                actual, result = self.invoke(["anime", "--json"])
            self.assertEqual(actual, code)
            self.assertEqual(result["error"]["code"], error)

    def test_legacy_json_cannot_enter_setup_and_closed_stdin_never_prompts(self):
        with patch.object(entrypoint, "load_config", return_value=AppConfig()), patch.object(entrypoint, "setup_qbittorrent", side_effect=AssertionError("setup")), patch.object(entrypoint, "prompt_startup_action", side_effect=AssertionError("prompt")):
            for argv in (["--json", "--setup-qbittorrent"], [], ["anime", "--non-interactive"], ["--json"], ["--json", "--language"]):
                with self.subTest(argv=argv):
                    code, result = self.invoke(argv)
                    self.assertEqual(code, 2)
                    self.assertIsNotNone(result["error"])

    def test_process_entrypoint_closed_stdin_and_schema(self):
        for argv, expected in (([], 2), (["schema"], 0), (["rules", "apply"], 2)):
            with self.subTest(argv=argv):
                process = subprocess.run([sys.executable, "-m", "mikancli", *argv], input="", capture_output=True, text=True, timeout=10, cwd=Path(__file__).resolve().parents[1])
                self.assertEqual(process.returncode, expected, process.stderr)
                self.assertEqual(process.stderr, "")
                result = json.loads(process.stdout)
                self.assertEqual(result["ok"], expected == 0)

    def test_machine_output_roundtrips_unicode_under_windows_codepages(self):
        with tempfile.TemporaryDirectory(prefix=".tmp_commands_", dir=Path(__file__).resolve().parents[1]) as directory:
            config = Path(directory) / "config.json"
            destination = "D:/Anime/\u6f2b\u753b\U0001f431"
            config.write_text(json.dumps({"default_save_path": destination}), encoding="utf-8")
            env = {**os.environ, "PYTHONIOENCODING": "gbk"}
            process = subprocess.run([sys.executable, "-m", "mikancli", "config", "show", "--config", str(config)], input=b"", capture_output=True, timeout=10, env=env, cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stderr, b"")
        result = json.loads(process.stdout.decode("ascii"))
        self.assertEqual(result["data"]["settings"]["default_save_path"], destination)
