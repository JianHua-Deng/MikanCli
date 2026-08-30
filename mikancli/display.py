from __future__ import annotations

from datetime import datetime

from mikancli.core.models import MikanFeedItem, MikanSubgroup, RuleDraft
from mikancli.i18n import t


def print_text_summary(draft: RuleDraft) -> int:
    """Print a human-readable summary of a rule draft. Returns 0 after writing the summary and any next-step notes to stdout."""
    print()
    print(t("display.rule_header"))
    print(t("display.keyword", value=draft.keyword))
    print(t("display.normalized_keyword", value=draft.normalized_keyword))
    print(t("display.rule_name", value=draft.rule_name))
    print(t("display.mikan_title", value=draft.mikan_title or t("common.not_found")))
    print(t("display.mikan_subgroup", value=draft.mikan_subgroup or t("common.not_found")))
    print(t("display.mikan_page", value=draft.mikan_page_url or t("common.not_found")))
    print(t("display.feed_url", value=draft.feed_url or t("common.not_found")))
    print(
        t(
            "display.must_contain",
            value=", ".join(draft.must_contain) if draft.must_contain else t("common.none"),
        )
    )
    print(
        t(
            "display.must_not_contain",
            value=", ".join(draft.must_not_contain) if draft.must_not_contain else t("common.none"),
        )
    )
    print(t("display.save_path", value=draft.save_path or t("common.not_set")))
    print(t("display.rule_footer"))
    print()

    for note in draft.notes:
        print(t("display.next_step", value=note))

    return 0


def format_size(size_bytes: int | None) -> str:
    """Format a byte count into a compact display string. Example: format_size(1536) returns "1.5 KB"."""
    if size_bytes is None:
        return t("common.unknown")

    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024

    return f"{size_bytes} B"


def format_timestamp(value: str | None) -> str:
    """Format an ISO timestamp for feed preview display, leaving unknown formats unchanged. Example: format_timestamp("2025-11-13T19:15:26") returns "2025/11/13 19:15"."""
    if not value:
        return t("common.unknown")

    try:
        return datetime.fromisoformat(value).strftime("%Y/%m/%d %H:%M")
    except ValueError:
        return value


def build_feed_preview_text(
    subgroup: MikanSubgroup,
    feed_items: tuple[MikanFeedItem, ...],
) -> str:
    """Build the text shown before the user confirms a subgroup RSS feed. Returns a multi-line preview string containing the feed URL and any recent feed items."""
    lines = [
        t("display.feed_preview", title=subgroup.title),
        t("display.feed_url_plain", url=subgroup.feed_url),
        t("display.items", count=len(feed_items)),
        "",
    ]

    if not feed_items:
        lines.append(t("display.feed_empty"))
        return "\n".join(lines)

    for index, item in enumerate(feed_items, start=1):
        lines.append(f"{index}. {item.title}")
        lines.append(
            "   "
            + t(
                "display.size_updated",
                size=format_size(item.content_length),
                updated=format_timestamp(item.published_at),
            )
        )

    return "\n".join(lines)
