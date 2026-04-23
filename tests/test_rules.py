import unittest

from mikancli.core.models import MikanBangumi, MikanSubgroup, SearchRequest
from mikancli.core.rules import build_rule_draft


class RuleDraftTests(unittest.TestCase):
    def test_build_rule_draft_uses_selected_subgroup_and_include_words(self) -> None:
        draft = build_rule_draft(
            SearchRequest(
                keyword="  Solo Leveling  ",
                include_words=("HEVC", "10-bit"),
                exclude_words=("720p", "  "),
                save_path="D:\\Anime\\Solo Leveling",
            ),
            bangumi=MikanBangumi(
                bangumi_id=3560,
                title="\u6211\u72ec\u81ea\u5347\u7ea7 \u7b2c\u4e8c\u5b63 -\u8d77\u4e8e\u6697\u5f71-",
                page_url="https://mikanani.me/Home/Bangumi/3560",
                feed_url="https://mikanani.me/RSS/Bangumi?bangumiId=3560",
            ),
            subgroup=MikanSubgroup(
                subgroup_id=370,
                title="LoliHouse",
                feed_url="https://mikanani.me/RSS/Bangumi?bangumiId=3560&subgroupid=370",
                publish_group_url="https://mikanani.me/Home/PublishGroup/223",
            ),
            notes=("qBittorrent submission not implemented yet.",),
        )

        self.assertEqual(draft.keyword, "Solo Leveling")
        self.assertEqual(draft.normalized_keyword, "solo leveling")
        self.assertEqual(draft.rule_name, "Solo Leveling")
        self.assertEqual(draft.must_contain, ("LoliHouse", "HEVC", "10-bit"))
        self.assertEqual(draft.must_not_contain, ("720p",))
        self.assertEqual(draft.mikan_subgroup, "LoliHouse")
        self.assertEqual(
            draft.feed_url,
            "https://mikanani.me/RSS/Bangumi?bangumiId=3560&subgroupid=370",
        )


if __name__ == "__main__":
    unittest.main()
