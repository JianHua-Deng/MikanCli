import unittest

from mikancli.integrations.mikan import (
    build_bangumi_feed_url,
    build_bangumi_page_url,
    build_search_url,
    build_subgroup_feed_url,
    parse_bangumi_subgroups,
    parse_feed_items,
    parse_search_results,
)

SEARCH_HTML = """
<html>
  <body>
    <ul class="list-inline an-ul" style="margin-top:20px;">
      <li>
        <a href="/Home/Bangumi/3560" target="_blank">
          <span data-src="/images/Bangumi/202501/2d4ee11e.jpg" class="b-lazy"></span>
          <div class="an-info">
            <div class="an-info-group">
              <div class="an-text" title="&#x6211;&#x72EC;&#x81EA;&#x5347;&#x7EA7; &#x7B2C;&#x4E8C;&#x5B63; -&#x8D77;&#x4E8E;&#x6697;&#x5F71;-">
                &#x6211;&#x72EC;&#x81EA;&#x5347;&#x7EA7; &#x7B2C;&#x4E8C;&#x5B63; -&#x8D77;&#x4E8E;&#x6697;&#x5F71;-
              </div>
            </div>
          </div>
        </a>
      </li>
      <li>
        <a href="/Home/Bangumi/3247" target="_blank">
          <div class="an-info">
            <div class="an-info-group">
              <div class="an-text" title="&#x6211;&#x72EC;&#x81EA;&#x5347;&#x7EA7;">
                &#x6211;&#x72EC;&#x81EA;&#x5347;&#x7EA7;
              </div>
            </div>
          </div>
        </a>
      </li>
    </ul>
  </body>
</html>
"""

BANGUMI_HTML = """
<div class="subgroup-text" id="1230">
    <a href="/Home/PublishGroup/1003" target="_blank" style="color: #3bc0c3;">Prejudice-Studio</a>
    <a href="/RSS/Bangumi?bangumiId=3247&subgroupid=1230" class="mikan-rss" target="_blank"><i class="fa fa-rss-square"></i></a>
</div>
<div class="episode-table"></div>
<div class="subgroup-text" id="370">
    <a href="/Home/PublishGroup/223" target="_blank" style="color: #3bc0c3;">LoliHouse</a>
    <a href="/RSS/Bangumi?bangumiId=3247&amp;subgroupid=370" class="mikan-rss" target="_blank"><i class="fa fa-rss-square"></i></a>
</div>
<div class="episode-table"></div>
"""

RSS_XML = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:mikan="https://mikanani.me/0.1/">
  <channel>
    <title>Mikan Project - Test Feed</title>
    <item>
      <guid isPermaLink="false">Item 1</guid>
      <link>https://mikanani.me/Home/Episode/abc</link>
      <title>Episode 01</title>
      <description>Episode 01 [4.2 GB]</description>
      <mikan:torrent>
        <mikan:link>https://mikanani.me/Home/Episode/abc</mikan:link>
        <mikan:contentLength>4509715456</mikan:contentLength>
        <mikan:pubDate>2025-11-13T19:15:26.336282</mikan:pubDate>
      </mikan:torrent>
      <enclosure type="application/x-bittorrent" length="4509715456" url="https://mikanani.me/Download/test.torrent" />
    </item>
  </channel>
</rss>
"""


class MikanTests(unittest.TestCase):
    def test_build_urls(self) -> None:
        self.assertEqual(
            build_search_url("solo leveling"),
            "https://mikanani.me/Home/Search?searchstr=solo%20leveling",
        )
        self.assertEqual(
            build_bangumi_page_url(3560),
            "https://mikanani.me/Home/Bangumi/3560",
        )
        self.assertEqual(
            build_bangumi_feed_url(3560),
            "https://mikanani.me/RSS/Bangumi?bangumiId=3560",
        )
        self.assertEqual(
            build_subgroup_feed_url(3247, 370),
            "https://mikanani.me/RSS/Bangumi?bangumiId=3247&subgroupid=370",
        )

    def test_parse_search_results_extracts_unique_bangumi_candidates(self) -> None:
        results = parse_search_results(SEARCH_HTML)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].bangumi_id, 3560)
        self.assertEqual(results[0].title, "我独自升级 第二季 -起于暗影-")
        self.assertEqual(
            results[0].page_url,
            "https://mikanani.me/Home/Bangumi/3560",
        )
        self.assertEqual(
            results[0].feed_url,
            "https://mikanani.me/RSS/Bangumi?bangumiId=3560",
        )

    def test_parse_bangumi_subgroups_extracts_group_specific_feeds(self) -> None:
        results = parse_bangumi_subgroups(BANGUMI_HTML, bangumi_id=3247)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].subgroup_id, 1230)
        self.assertEqual(results[0].title, "Prejudice-Studio")
        self.assertEqual(
            results[0].feed_url,
            "https://mikanani.me/RSS/Bangumi?bangumiId=3247&subgroupid=1230",
        )
        self.assertEqual(
            results[0].publish_group_url,
            "https://mikanani.me/Home/PublishGroup/1003",
        )

    def test_parse_feed_items_reads_title_size_and_timestamp(self) -> None:
        items = parse_feed_items(RSS_XML)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Episode 01")
        self.assertEqual(items[0].episode_url, "https://mikanani.me/Home/Episode/abc")
        self.assertEqual(
            items[0].torrent_url,
            "https://mikanani.me/Download/test.torrent",
        )
        self.assertEqual(items[0].content_length, 4509715456)
        self.assertEqual(items[0].published_at, "2025-11-13T19:15:26.336282")


if __name__ == "__main__":
    unittest.main()
