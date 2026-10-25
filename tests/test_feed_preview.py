from __future__ import annotations

from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from rich.console import Console
from rich.theme import Theme

from mikancli.core.models import MikanFeedItem, MikanSubgroup
from mikancli.display import build_feed_preview_page_text, print_feed_preview_page
from mikancli.i18n import get_language, set_language, t


class FeedPreviewTests(TestCase):
    def test_rich_preview_preserves_pages_and_literal_content(self) -> None:
        self.addCleanup(set_language, get_language())
        subgroup = MikanSubgroup(534, "[bold]天月动漫[/bold]" * 5,
                                "https://example.test/rss?title=[OnePiece]&group=534" * 2)
        items = tuple(MikanFeedItem(title=f"[bold]动画[/bold][{i}]:smile:", content_length=1536)
                      for i in range(1, 14))
        theme = Theme({"heading": "cyan", "note": "dim"})
        for language in ("en", "zh-CN"):
            set_language(language)
            for width in (40, 120):
                for page in (1, 2):
                    with self.subTest(language=language, width=width, page=page):
                        output = StringIO()
                        terminal = Console(file=output, width=width, height=40, force_terminal=True,
                                           color_system=None, theme=theme)
                        with patch("mikancli.display.console", terminal):
                            print_feed_preview_page(subgroup, items, page=page)
                        framed = output.getvalue()
                        self.assertIn("│", framed)
                        rendered = "".join(char for char in framed
                                           if not char.isspace() and char not in "╭╮╰╯┌┐└┘│─")
                        expected = build_feed_preview_page_text(subgroup, items, page=page)
                        self.assertEqual(rendered, "".join(expected.split()))
                        self.assertEqual("[13]" in rendered, page == 2)
                        self.assertEqual("[1]" in rendered, page == 1)
                        self.assertNotIn("\x1b", rendered)

    def test_redirected_empty_preview_keeps_plain_text(self) -> None:
        subgroup = MikanSubgroup(534, "[bold]Group[/bold]", "https://example.test/rss")
        output = StringIO()
        with patch("mikancli.display.console", Console(file=output, width=20, force_terminal=False)):
            print_feed_preview_page(subgroup, (), page=1)
        self.assertEqual(output.getvalue(), build_feed_preview_page_text(subgroup, (), page=1) + "\n")
        self.assertIn(t("display.feed_empty"), output.getvalue())

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
