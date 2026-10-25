from __future__ import annotations

import copy
from unittest import TestCase
from unittest.mock import patch

from mikancli.core.models import MikanSubgroup, QBittorrentSettings
from mikancli.integrations.mikan import MikanLookupError
from mikancli.integrations.qbittorrent_client import QBittorrentError
from mikancli.services.errors import CommandError
from mikancli.services.rules import apply_plan, build_plan, get_rule, plan_schema, validate_plan


FEED = "https://mikanani.me/RSS/Bangumi?bangumiId=123&subgroupid=456"
SETTINGS = QBittorrentSettings("http://localhost:8080", "user", "password")


def sample_plan() -> dict:
    return {
        "plan_version": 1,
        "rule_name": "One Piece",
        "feed_url": FEED,
        "feed_path": "One Piece",
        "rule_definition": {
            "enabled": True,
            "mustContain": "(?=.*1080p).*",
            "mustNotContain": "720p",
            "useRegex": True,
            "episodeFilter": "",
            "smartFilter": False,
            "affectedFeeds": [FEED],
            "ignoreDays": 0,
            "addPaused": True,
            "assignedCategory": "Anime",
            "savePath": "D:/Anime/One Piece",
        },
    }


class FakeClient:
    def __init__(self, *, rules: dict | None = None, feed_exists: bool = False):
        self.rules = copy.deepcopy(rules or {})
        self.tree = {"Anime": {"feed": {"url": FEED}}} if feed_exists else {}
        self.calls: list[object] = []
        self.failure: str | None = None
        self.rewrite_field: str | None = None
        self.fail_verification = False
        self.rule_reads = 0

    def login(self):
        self.calls.append("login")
        if self.failure == "login":
            raise QBittorrentError("authentication failed")

    def get_auto_downloading_rules(self):
        self.calls.append("rules")
        self.rule_reads += 1
        if self.fail_verification and self.rule_reads > 1:
            raise QBittorrentError("connection lost during verification")
        return copy.deepcopy(self.rules)

    def get_rss_items(self):
        self.calls.append("feeds")
        return copy.deepcopy(self.tree)

    def add_feed(self, url, *, path):
        self.calls.append(("add_feed", url, path))
        self.tree[path] = {"url": url}
        if self.failure == "add_feed":
            raise QBittorrentError("response lost after feed write")

    def set_auto_downloading_rule(self, name, definition):
        self.calls.append(("set_rule", name, copy.deepcopy(definition)))
        if self.failure == "set_rule":
            raise QBittorrentError("rule write failed")
        self.rules[name] = copy.deepcopy(definition)
        if self.rewrite_field is not None:
            self.rules[name][self.rewrite_field] = "unexpected server value"

    @property
    def writes(self):
        return [call for call in self.calls if isinstance(call, tuple)]


class BuildPlanTests(TestCase):
    def test_build_resolves_only_explicit_subgroup_and_does_not_include_history(self):
        subgroups = (
            MikanSubgroup(999, "First result", "https://example.test/wrong"),
            MikanSubgroup(456, "Chosen group", FEED),
        )
        with patch("mikancli.services.rules.fetch_mikan_subgroups", return_value=subgroups) as fetch:
            plan = build_plan(
                bangumi_id=123, subgroup_id=456, name=" One   Piece ",
                include=("1080p",), exclude=("720p",), min_episode=1126,
                save_path="D:/Anime/One Piece", category=" Anime ", add_paused=True,
                timeout=9,
            )
        fetch.assert_called_once_with(123, timeout=9.0)
        self.assertEqual(plan["rule_name"], "One Piece")
        self.assertEqual(plan["feed_url"], FEED)
        definition = plan["rule_definition"]
        self.assertIn("1080p", definition["mustContain"])
        self.assertIn("1126", definition["mustContain"])
        self.assertEqual(definition["mustNotContain"], "720p")
        self.assertEqual(definition["assignedCategory"], "Anime")
        self.assertEqual(definition["savePath"], "D:/Anime/One Piece")
        self.assertIs(definition["addPaused"], True)
        self.assertNotIn("previouslyMatchedEpisodes", definition)
        self.assertNotIn("lastMatch", definition)
        self.assertNotIn("password", str(plan))

    def test_missing_subgroup_does_not_fall_back_to_first(self):
        with patch("mikancli.services.rules.fetch_mikan_subgroups", return_value=(MikanSubgroup(9, "Other", FEED),)):
            with self.assertRaises(CommandError) as raised:
                build_plan(bangumi_id=123, subgroup_id=456, name="Test")
        self.assertEqual(raised.exception.code, "NOT_FOUND")
        self.assertEqual(raised.exception.exit_code, 3)

    def test_bad_arguments_fail_before_mikan_request(self):
        cases = (
            {"bangumi_id": True}, {"subgroup_id": -1}, {"name": " "},
            {"min_episode": True}, {"add_paused": 1}, {"timeout": float("nan")},
            {"timeout": 10 ** 1000},
            {"include": ("",)}, {"include": "1080p"}, {"feed_path": ""},
        )
        for invalid in cases:
            with self.subTest(invalid=invalid), patch("mikancli.services.rules.fetch_mikan_subgroups") as fetch:
                arguments = {"bangumi_id": 123, "subgroup_id": 456, "name": "Test", **invalid}
                with self.assertRaises(CommandError) as raised:
                    build_plan(**arguments)
                self.assertEqual(raised.exception.code, "INVALID_ARGUMENT")
                fetch.assert_not_called()

    def test_lookup_failure_does_not_return_a_draft(self):
        with patch("mikancli.services.rules.fetch_mikan_subgroups", side_effect=MikanLookupError("unavailable")):
            with self.assertRaises(CommandError):
                build_plan(bangumi_id=123, subgroup_id=456, name="Test")


class PlanValidationTests(TestCase):
    def test_validated_plan_is_independent_of_input(self):
        original = sample_plan()
        validated = validate_plan(original)
        validated["rule_definition"]["affectedFeeds"].clear()
        self.assertEqual(original["rule_definition"]["affectedFeeds"], [FEED])

    def test_rejects_ambiguous_or_unsafe_plans_before_constructing_client(self):
        cases = []
        for field, value in (
            ("plan_version", True), ("plan_version", 2), ("rule_name", " Name "),
            ("rule_name", ""), ("feed_path", "folder\nname"),
            ("feed_url", "file:///tmp/feed"), ("feed_url", "https://user:secret@example.test/rss"),
            ("feed_url", "https://example.test/rss#fragment"), ("feed_url", "http://example.test:invalid/rss"),
            ("unexpected", "value"),
        ):
            plan = sample_plan()
            plan[field] = value
            cases.append(plan)
        for field, value in (
            ("enabled", 1), ("addPaused", "false"), ("ignoreDays", False),
            ("ignoreDays", -1), ("mustContain", "x" * 65537),
            ("affectedFeeds", [FEED, "https://example.test/other"]),
            ("assignedCategory", " Anime "), ("lastMatch", ""),
        ):
            plan = sample_plan()
            plan["rule_definition"][field] = value
            cases.append(plan)
        plan = sample_plan()
        del plan["rule_definition"]["savePath"]
        cases.append(plan)
        cases.extend((None, [], {"data": sample_plan()}))
        for invalid in cases:
            with self.subTest(invalid=invalid), patch("mikancli.services.rules.QBittorrentClient") as client:
                with self.assertRaises(CommandError) as raised:
                    apply_plan(SETTINGS, invalid)
                self.assertEqual(raised.exception.code, "INVALID_ARGUMENT")
                self.assertEqual(raised.exception.exit_code, 2)
                client.assert_not_called()

    def test_schema_lists_every_required_field_and_excludes_history(self):
        schema = plan_schema()
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(sample_plan()))
        rule = schema["properties"]["rule_definition"]
        self.assertFalse(rule["additionalProperties"])
        self.assertEqual(set(rule["required"]), set(sample_plan()["rule_definition"]))
        self.assertNotIn("lastMatch", rule["properties"])


class ApplyPlanTests(TestCase):
    def apply_with(self, client, *, plan=None, if_exists="fail"):
        with patch("mikancli.services.rules.QBittorrentClient", return_value=client) as constructor:
            result = apply_plan(SETTINGS, plan or sample_plan(), if_exists=if_exists, timeout=7)
        constructor.assert_called_once_with(SETTINGS, timeout=7.0)
        return result

    def test_create_then_repeat_is_idempotent_without_resetting_history(self):
        client = FakeClient()
        created = self.apply_with(client)
        self.assertEqual(created["status"], "created")
        self.assertEqual([call[0] for call in client.writes], ["add_feed", "set_rule"])
        self.assertEqual(created["verification"], {"feed_verified": True, "rule_verified": True, "mismatched_fields": []})
        client.rules["One Piece"]["lastMatch"] = "server history"
        client.rules["One Piece"]["previouslyMatchedEpisodes"] = ["1126"]
        client.calls.clear()
        repeated = self.apply_with(client)
        self.assertEqual(repeated["status"], "unchanged")
        self.assertFalse(repeated["rule_written"])
        self.assertEqual(client.writes, [])
        self.assertEqual(client.rules["One Piece"]["lastMatch"], "server history")

    def test_changed_existing_rule_fails_before_any_feed_or_rule_write(self):
        definition = sample_plan()["rule_definition"]
        definition["assignedCategory"] = "Different"
        client = FakeClient(rules={"One Piece": definition})
        with self.assertRaises(CommandError) as raised:
            self.apply_with(client)
        self.assertEqual(raised.exception.code, "CONFLICT")
        self.assertEqual(raised.exception.exit_code, 4)
        self.assertEqual(raised.exception.details["mismatched_fields"], ["assignedCategory"])
        self.assertEqual(client.calls, ["login", "rules"])

    def test_explicit_replace_updates_rule_without_adding_an_existing_feed(self):
        definition = sample_plan()["rule_definition"]
        definition["savePath"] = "old path"
        client = FakeClient(rules={"One Piece": definition}, feed_exists=True)
        result = self.apply_with(client, if_exists="replace")
        self.assertEqual(result["status"], "updated")
        self.assertEqual([call[0] for call in client.writes], ["set_rule"])
        self.assertEqual(client.rules["One Piece"], sample_plan()["rule_definition"])

    def test_replace_preserves_server_history_and_unplanned_settings(self):
        definition = sample_plan()["rule_definition"]
        definition.update({
            "savePath": "old path",
            "lastMatch": "Fri, 23 Oct 2026 12:00:00 +0000",
            "previouslyMatchedEpisodes": ["1126", "1127"],
            "priority": 17,
            "torrentContentLayout": "NoSubfolder",
        })
        client = FakeClient(rules={"One Piece": definition}, feed_exists=True)
        self.apply_with(client, if_exists="replace")
        written = client.rules["One Piece"]
        self.assertEqual(written["savePath"], sample_plan()["rule_definition"]["savePath"])
        for field in ("lastMatch", "previouslyMatchedEpisodes", "priority", "torrentContentLayout"):
            self.assertEqual(written[field], definition[field])
        self.assertNotIn("lastMatch", sample_plan()["rule_definition"])

    def test_replace_updates_nested_parameters_and_preserves_advanced_options(self):
        definition = sample_plan()["rule_definition"]
        definition["torrentParams"] = {
            "stopped": False, "category": "Old", "save_path": "old path",
            "use_auto_tmm": True, "tags": ["keep-me"],
            "upload_limit": 1234, "content_layout": "NoSubfolder",
        }
        client = FakeClient(rules={"One Piece": definition}, feed_exists=True)
        result = self.apply_with(client, if_exists="replace")
        written = client.rules["One Piece"]
        self.assertEqual(result["status"], "updated")
        self.assertEqual(written["torrentParams"], {
            "stopped": True, "category": "Anime", "save_path": "D:/Anime/One Piece",
            "use_auto_tmm": False, "tags": ["keep-me"],
            "upload_limit": 1234, "content_layout": "NoSubfolder",
        })
        self.assertEqual(definition["torrentParams"]["category"], "Old")

    def test_conflict_compares_effective_nested_parameters_before_writes(self):
        definition = sample_plan()["rule_definition"]
        definition["torrentParams"] = {
            "stopped": True, "category": "Different", "save_path": definition["savePath"],
        }
        client = FakeClient(rules={"One Piece": definition}, feed_exists=True)
        with self.assertRaises(CommandError) as raised:
            self.apply_with(client)
        self.assertEqual(raised.exception.code, "CONFLICT")
        self.assertEqual(raised.exception.details["mismatched_fields"], ["assignedCategory"])
        self.assertEqual(client.writes, [])

    def test_verification_uses_nested_parameters_even_if_legacy_fields_match(self):
        client = FakeClient(feed_exists=True)
        original_write = client.set_auto_downloading_rule

        def override_nested(name, definition):
            original_write(name, definition)
            client.rules[name]["torrentParams"] = {
                "stopped": False, "category": "Anime", "save_path": definition["savePath"],
            }

        with patch.object(client, "set_auto_downloading_rule", side_effect=override_nested):
            with self.assertRaises(CommandError) as raised:
                self.apply_with(client)
        self.assertEqual(raised.exception.code, "PARTIAL_SUCCESS")
        self.assertEqual(raised.exception.details["verification"]["mismatched_fields"], ["addPaused"])

    def test_identical_nested_rule_is_unchanged_despite_stale_legacy_fields(self):
        definition = sample_plan()["rule_definition"]
        definition["torrentParams"] = {
            "stopped": definition["addPaused"], "category": definition["assignedCategory"],
            "save_path": definition["savePath"], "tags": ["preserve"],
        }
        definition["savePath"] = "stale legacy value"
        definition["addPaused"] = None
        client = FakeClient(rules={"One Piece": definition}, feed_exists=True)
        result = self.apply_with(client)
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(client.writes, [])

    def test_auto_tmm_cannot_override_an_explicit_planned_save_path(self):
        definition = sample_plan()["rule_definition"]
        definition["torrentParams"] = {
            "stopped": definition["addPaused"], "category": definition["assignedCategory"],
            "save_path": definition["savePath"], "use_auto_tmm": True,
        }
        client = FakeClient(rules={"One Piece": definition}, feed_exists=True)
        with self.assertRaises(CommandError) as raised:
            self.apply_with(client)
        self.assertEqual(raised.exception.details["mismatched_fields"], ["savePath"])
        self.assertEqual(client.writes, [])
        result = self.apply_with(client, if_exists="replace")
        self.assertEqual(result["status"], "updated")
        self.assertIs(client.rules["One Piece"]["torrentParams"]["use_auto_tmm"], False)

    def test_equivalent_server_save_paths_are_idempotent(self):
        pairs = (
            (r"D:\Anime\One Piece", "D:/Anime/One Piece/"),
            ("D:/Anime/One Piece/", r"D:\Anime\One Piece"),
            ("D:/", "D:\\"),
            (r"\\Server\Share\Anime", "//Server/Share/Anime/"),
            (r"\\Server\Share", "//Server/Share/"),
            ("/downloads/anime/", "/downloads/anime"),
            (r"/downloads/anime\version", "/downloads/anime\\version/"),
        )
        for planned_path, server_path in pairs:
            with self.subTest(planned=planned_path, server=server_path):
                plan = sample_plan()
                plan["rule_definition"]["savePath"] = planned_path
                definition = copy.deepcopy(plan["rule_definition"])
                definition["savePath"] = server_path
                client = FakeClient(rules={"One Piece": definition}, feed_exists=True)
                result = self.apply_with(client, plan=plan)
                self.assertEqual(result["status"], "unchanged")
                self.assertTrue(result["verification"]["rule_verified"])
                self.assertEqual(client.writes, [])

    def test_save_paths_do_not_case_fold_or_treat_posix_backslashes_as_separators(self):
        pairs = (
            ("D:/Anime/One Piece", "D:/anime/One Piece"),
            (r"/downloads/anime\version", "/downloads/anime/version"),
            ("/Downloads/Anime", "/downloads/anime"),
            ("D:/", "D:"),
            ("", "."),
        )
        for planned_path, server_path in pairs:
            with self.subTest(planned=planned_path, server=server_path):
                plan = sample_plan()
                plan["rule_definition"]["savePath"] = planned_path
                definition = copy.deepcopy(plan["rule_definition"])
                definition["savePath"] = server_path
                client = FakeClient(rules={"One Piece": definition}, feed_exists=True)
                with self.assertRaises(CommandError) as raised:
                    self.apply_with(client, plan=plan)
                self.assertEqual(raised.exception.code, "CONFLICT")
                self.assertEqual(raised.exception.details["mismatched_fields"], ["savePath"])
                self.assertEqual(client.writes, [])

    def test_post_write_verification_accepts_normalized_windows_path_in_nested_params(self):
        plan = sample_plan()
        plan["rule_definition"]["savePath"] = r"D:\Anime\One Piece"
        client = FakeClient(feed_exists=True)
        original_write = client.set_auto_downloading_rule

        def normalize_saved_path(name, definition):
            original_write(name, definition)
            client.rules[name]["torrentParams"] = {
                "stopped": True, "category": "Anime", "save_path": "D:/Anime/One Piece/",
            }

        with patch.object(client, "set_auto_downloading_rule", side_effect=normalize_saved_path):
            result = self.apply_with(client, plan=plan)
        self.assertEqual(result["status"], "created")
        self.assertTrue(result["verification"]["rule_verified"])

    def test_identical_rule_repairs_missing_feed_without_rewriting_rule(self):
        client = FakeClient(rules={"One Piece": sample_plan()["rule_definition"]})
        result = self.apply_with(client)
        self.assertEqual(result["status"], "unchanged")
        self.assertTrue(result["feed_added"])
        self.assertEqual([call[0] for call in client.writes], ["add_feed"])

    def test_documented_scalar_feed_tree_is_recognized(self):
        client = FakeClient()
        client.tree = {"Anime": {"One Piece": FEED}}
        result = self.apply_with(client)
        self.assertTrue(result["verification"]["feed_verified"])
        self.assertEqual([call[0] for call in client.writes], ["set_rule"])

    def test_url_appearing_as_feed_metadata_does_not_count_as_feed(self):
        client = FakeClient()
        client.tree = {"Other": {
            "url": "https://example.test/other", "title": FEED,
            "articles": [{"url": FEED}],
        }}
        self.apply_with(client)
        self.assertEqual(client.writes[0][0], "add_feed")

    def test_rule_write_failure_reports_partial_with_completed_feed_stage(self):
        client = FakeClient()
        client.failure = "set_rule"
        with self.assertRaises(CommandError) as raised:
            self.apply_with(client)
        error = raised.exception
        self.assertEqual(error.code, "PARTIAL_SUCCESS")
        self.assertEqual(error.exit_code, 5)
        self.assertFalse(error.retryable)
        self.assertTrue(error.details["stages"]["feed_added"])
        self.assertTrue(error.details["stages"]["rule_write_attempted"])
        self.assertFalse(error.details["stages"]["rule_saved"])
        self.assertEqual(len(client.writes), 2)

    def test_unknown_feed_write_outcome_stops_without_attempting_rule(self):
        client = FakeClient()
        client.failure = "add_feed"
        with self.assertRaises(CommandError) as raised:
            self.apply_with(client)
        self.assertEqual(raised.exception.code, "PARTIAL_SUCCESS")
        self.assertTrue(raised.exception.details["stages"]["feed_add_attempted"])
        self.assertFalse(raised.exception.details["stages"]["feed_added"])
        self.assertEqual(len(client.writes), 1)

    def test_verification_checks_all_planned_fields(self):
        for field in ("mustContain", "mustNotContain", "savePath", "assignedCategory", "addPaused"):
            with self.subTest(field=field):
                client = FakeClient()
                client.rewrite_field = field
                with self.assertRaises(CommandError) as raised:
                    self.apply_with(client)
                self.assertEqual(raised.exception.code, "PARTIAL_SUCCESS")
                self.assertEqual(raised.exception.details["verification"]["mismatched_fields"], [field])
                self.assertTrue(raised.exception.details["verification"]["feed_verified"])

    def test_lost_verification_after_write_is_partial_and_not_retried(self):
        client = FakeClient()
        client.fail_verification = True
        with self.assertRaises(CommandError) as raised:
            self.apply_with(client)
        self.assertEqual(raised.exception.code, "PARTIAL_SUCCESS")
        self.assertTrue(raised.exception.details["stages"]["rule_saved"])
        self.assertFalse(raised.exception.details["stages"]["verification_completed"])
        self.assertEqual(len(client.writes), 2)

    def test_authentication_failure_is_not_reported_as_partial_success(self):
        client = FakeClient()
        client.failure = "login"
        with self.assertRaises(CommandError) as raised:
            self.apply_with(client)
        self.assertNotEqual(raised.exception.code, "PARTIAL_SUCCESS")
        self.assertEqual(client.writes, [])

    def test_invalid_overwrite_policy_fails_before_constructing_client(self):
        for invalid in ("overwrite", [], None):
            with self.subTest(invalid=invalid), patch("mikancli.services.rules.QBittorrentClient") as client:
                with self.assertRaises(CommandError) as raised:
                    apply_plan(SETTINGS, sample_plan(), if_exists=invalid)
                self.assertEqual(raised.exception.code, "INVALID_ARGUMENT")
                client.assert_not_called()

    def test_cancellation_before_writes_propagates_for_regular_interruption_handling(self):
        client = FakeClient()
        with patch.object(client, "login", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.apply_with(client)
        self.assertEqual(client.writes, [])

    def test_cancellation_during_feed_write_reports_unknown_partial_state(self):
        client = FakeClient()
        with patch.object(client, "add_feed", side_effect=KeyboardInterrupt):
            with self.assertRaises(CommandError) as raised:
                self.apply_with(client)
        error = raised.exception
        self.assertEqual(error.code, "PARTIAL_SUCCESS")
        self.assertEqual(error.exit_code, 5)
        self.assertEqual(error.details["cause"]["code"], "INTERRUPTED")
        self.assertTrue(error.details["stages"]["feed_add_attempted"])
        self.assertFalse(error.details["stages"]["feed_added"])
        self.assertFalse(error.details["stages"]["rule_write_attempted"])

    def test_cancellation_during_rule_write_preserves_completed_feed_stage(self):
        client = FakeClient()
        with patch.object(client, "set_auto_downloading_rule", side_effect=KeyboardInterrupt):
            with self.assertRaises(CommandError) as raised:
                self.apply_with(client)
        stages = raised.exception.details["stages"]
        self.assertEqual(raised.exception.code, "PARTIAL_SUCCESS")
        self.assertTrue(stages["feed_added"])
        self.assertTrue(stages["rule_write_attempted"])
        self.assertFalse(stages["rule_saved"])

    def test_cancellation_during_post_write_verification_reports_completed_writes(self):
        client = FakeClient()
        original_read = client.get_auto_downloading_rules

        def interrupt_verification():
            if client.rule_reads:
                raise KeyboardInterrupt
            return original_read()

        with patch.object(client, "get_auto_downloading_rules", side_effect=interrupt_verification):
            with self.assertRaises(CommandError) as raised:
                self.apply_with(client)
        stages = raised.exception.details["stages"]
        self.assertEqual(raised.exception.code, "PARTIAL_SUCCESS")
        self.assertTrue(stages["feed_added"])
        self.assertTrue(stages["rule_saved"])
        self.assertFalse(stages["verification_completed"])


class GetRuleTests(TestCase):
    def test_get_is_read_only_and_reports_actual_settings_and_feed_presence(self):
        definition = sample_plan()["rule_definition"]
        definition["lastMatch"] = "server history"
        definition["affectedFeeds"].append("https://example.test/missing")
        client = FakeClient(rules={"One Piece": definition}, feed_exists=True)
        with patch("mikancli.services.rules.QBittorrentClient", return_value=client) as constructor:
            result = get_rule(SETTINGS, "One Piece", timeout=4)
        constructor.assert_called_once_with(SETTINGS, timeout=4.0)
        self.assertEqual(result["rule_definition"], definition)
        self.assertFalse(result["feed_exists"])
        self.assertEqual(result["feeds"], [{"feed_url": FEED, "exists": True}, {"feed_url": "https://example.test/missing", "exists": False}])
        self.assertEqual(client.writes, [])

    def test_missing_rule_has_nonzero_not_found_error(self):
        client = FakeClient()
        with patch("mikancli.services.rules.QBittorrentClient", return_value=client):
            with self.assertRaises(CommandError) as raised:
                get_rule(SETTINGS, "Missing")
        self.assertEqual(raised.exception.code, "NOT_FOUND")
        self.assertEqual(raised.exception.exit_code, 3)
        self.assertEqual(client.calls, ["login", "rules"])
