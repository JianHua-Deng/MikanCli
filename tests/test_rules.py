import unittest

from autofeedsync.models import SearchRequest
from autofeedsync.rules import build_rule_draft


class RuleDraftTests(unittest.TestCase):
    def test_build_rule_draft_combines_group_resolution_and_includes(self) -> None:
        draft = build_rule_draft(
            SearchRequest(
                keyword="  Solo Leveling  ",
                group="SubsPlease",
                resolution="1080p",
                include_words=("HEVC", "subsplease"),
                exclude_words=("720p", "  "),
                save_path="D:\\Anime\\Solo Leveling",
            )
        )

        self.assertEqual(draft.keyword, "Solo Leveling")
        self.assertEqual(draft.normalized_keyword, "solo leveling")
        self.assertEqual(draft.rule_name, "Solo Leveling")
        self.assertEqual(draft.must_contain, ("SubsPlease", "1080p", "HEVC"))
        self.assertEqual(draft.must_not_contain, ("720p",))
        self.assertEqual(draft.save_path, "D:\\Anime\\Solo Leveling")


if __name__ == "__main__":
    unittest.main()
