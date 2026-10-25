import json
from contextlib import redirect_stdout
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from mikancli.cli import entrypoint, search_flow
from mikancli.core.models import AppConfig, MikanBangumi, MikanSubgroup
from mikancli.i18n import get_language, set_language


class JsonOutputTests(TestCase):
    def test_json_draft_bypasses_rich_feedback_and_loading(self) -> None:
        self.addCleanup(set_language, get_language())
        title = "[bold]Anime[/bold]"
        bangumi = MikanBangumi(1, title, "https://example.test/anime", "https://example.test/rss")
        subgroup = MikanSubgroup(534, "Group", "https://example.test/rss")
        output = StringIO()
        with (
            patch.object(entrypoint, "load_config", return_value=AppConfig()),
            patch.object(search_flow, "search_mikan_bangumi", return_value=(bangumi,)),
            patch.object(search_flow, "fetch_mikan_subgroups", return_value=(subgroup,)),
            patch.object(search_flow, "loading", side_effect=AssertionError("JSON invoked loading UI")),
            patch.object(entrypoint, "print_message", side_effect=AssertionError("JSON invoked feedback UI")),
            redirect_stdout(output),
        ):
            self.assertEqual(entrypoint.main([title, "--json", "--save-path", "C:/Anime"]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["keyword"], title)
        self.assertEqual(result["feed_url"], subgroup.feed_url)
