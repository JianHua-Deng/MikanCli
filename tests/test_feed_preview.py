from __future__ import annotations

from unittest import TestCase

from mikancli.core.models import MikanFeedItem, MikanSubgroup
from mikancli.display import build_feed_preview_page_text


class FeedPreviewTests(TestCase):
    def test_feed_preview_paginates_items(self) -> None:
        subgroup = MikanSubgroup(
            subgroup_id=534,
            title="天月动漫&发布组",
            feed_url="https://example.test/rss",
        )
        items = tuple(
            MikanFeedItem(title=f"[Skymoon-Raws][One Piece][{episode}][1080p]")
            for episode in range(1126, 1141)
        )

        first_page = build_feed_preview_page_text(
            subgroup,
            items,
            page=1,
            page_size=12,
        )
        second_page = build_feed_preview_page_text(
            subgroup,
            items,
            page=2,
            page_size=12,
        )

        self.assertIn("Items: 15 | Page 1/2", first_page)
        self.assertIn("[1126]", first_page)
        self.assertNotIn("[1138]", first_page)
        self.assertIn("Items: 15 | Page 2/2", second_page)
        self.assertIn("[1138]", second_page)
