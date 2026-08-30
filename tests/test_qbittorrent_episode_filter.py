from __future__ import annotations

import re
from unittest import TestCase

from mikancli.core.models import RuleDraft
from mikancli.integrations.qbittorrent import (
    build_min_episode_title_regex,
    build_qbittorrent_rule_definition,
    build_required_terms_regex,
)


class QBittorrentEpisodeFilterTests(TestCase):
    def test_min_episode_regex_matches_anime_dash_title_at_threshold(self) -> None:
        pattern = re.compile(build_min_episode_title_regex(1126))

        self.assertIsNotNone(pattern.search("[SubsPlease] One Piece - 1126 (1080p)"))
        self.assertIsNotNone(pattern.search("[SubsPlease] One Piece - 1127 (1080p)"))
        self.assertIsNotNone(pattern.search("[SubsPlease] One Piece - 1130 (1080p)"))
        self.assertIsNotNone(pattern.search("[SubsPlease] One Piece - 1200 (1080p)"))
        self.assertIsNotNone(pattern.search("[SubsPlease] One Piece - 10000 (1080p)"))

    def test_min_episode_regex_matches_bracketed_episode_title(self) -> None:
        pattern = re.compile(build_min_episode_title_regex(1126))

        self.assertIsNotNone(
            pattern.search(
                "[Skymoon-Raws][One Piece][1175][ViuTV][WEB-RIP][CHT][SRT][1080p][MKV]"
            )
        )
        self.assertIsNotNone(
            pattern.search(
                "[Skymoon-Raws][One Piece][1126][ViuTV][WEB-RIP][CHT][SRT][1080p][MKV]"
            )
        )

    def test_min_episode_regex_rejects_anime_dash_title_below_threshold(self) -> None:
        pattern = re.compile(build_min_episode_title_regex(1126))

        self.assertIsNone(pattern.search("[SubsPlease] One Piece - 1125 (1080p)"))
        self.assertIsNone(pattern.search("[SubsPlease] One Piece - 1119 (1080p)"))
        self.assertIsNone(pattern.search("[SubsPlease] One Piece - 999 (1080p)"))
        self.assertIsNone(
            pattern.search(
                "[Skymoon-Raws][One Piece][1125][ViuTV][WEB-RIP][CHT][SRT][1080p][MKV]"
            )
        )

    def test_required_terms_regex_combines_literals_and_min_episode(self) -> None:
        pattern = re.compile(
            build_required_terms_regex(("SubsPlease",), min_episode=1126)
        )

        self.assertIsNotNone(pattern.search("[SubsPlease] One Piece - 1126 (1080p)"))
        self.assertIsNone(pattern.search("[OtherGroup] One Piece - 1126 (1080p)"))
        self.assertIsNone(pattern.search("[SubsPlease] One Piece - 1125 (1080p)"))

    def test_qbittorrent_rule_definition_enables_regex_for_min_episode(self) -> None:
        draft = RuleDraft(
            keyword="One Piece",
            normalized_keyword="one piece",
            rule_name="One Piece",
            must_contain=(),
            must_not_contain=(),
            min_episode=1126,
            feed_url="https://example.test/rss",
        )

        definition = build_qbittorrent_rule_definition(draft)

        self.assertIs(definition["useRegex"], True)
        self.assertEqual(
            definition["mustContain"],
            (
                r"(?=.*(?:-\s*0*(?:1126|112[7-9]|11[3-9]\d|1[2-9]\d{2}|"
                r"[2-9]\d{3}|[1-9]\d{4,})(?=\D|$)|\[\s*0*(?:1126|112[7-9]|"
                r"11[3-9]\d|1[2-9]\d{2}|[2-9]\d{3}|[1-9]\d{4,})\s*\])).*"
            ),
        )

    def test_min_episode_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            build_min_episode_title_regex(0)
