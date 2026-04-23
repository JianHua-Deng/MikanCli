from __future__ import annotations

from datetime import datetime

from mikancli.core.models import MikanFeedItem, MikanSubgroup, RuleDraft


def print_text_summary(draft: RuleDraft) -> int:
    print()
    print("---- Rule Draft ----")
    print(f"Keyword: {draft.keyword}")
    print(f"Normalized keyword: {draft.normalized_keyword}")
    print(f"Rule name: {draft.rule_name}")
    print(f"Mikan title: {draft.mikan_title or '(not found)'}")
    print(f"Mikan subgroup: {draft.mikan_subgroup or '(not found)'}")
    print(f"Mikan page: {draft.mikan_page_url or '(not found)'}")
    print(f"Feed URL: {draft.feed_url or '(not found)'}")
    print(
        "Must contain: "
        + (", ".join(draft.must_contain) if draft.must_contain else "(none)")
    )
    print(
        "Must not contain: "
        + (", ".join(draft.must_not_contain) if draft.must_not_contain else "(none)")
    )
    print(f"Save path: {draft.save_path or '(not set)'}")
    print("---- End Rule Draft Summary ----")
    print()

    for note in draft.notes:
        print(f"Next step: {note}")

    return 0


def format_size(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "(unknown)"

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
    if not value:
        return "(unknown)"

    try:
        return datetime.fromisoformat(value).strftime("%Y/%m/%d %H:%M")
    except ValueError:
        return value


def build_feed_preview_text(
    subgroup: MikanSubgroup,
    feed_items: tuple[MikanFeedItem, ...],
) -> str:
    lines = [
        f"Subgroup preview: {subgroup.title}",
        f"Feed URL: {subgroup.feed_url}",
        f"Items: {len(feed_items)}",
        "",
    ]

    if not feed_items:
        lines.append("(The RSS feed is empty.)")
        return "\n".join(lines)

    for index, item in enumerate(feed_items, start=1):
        lines.append(f"{index}. {item.title}")
        lines.append(
            "   "
            f"Size: {format_size(item.content_length)} | "
            f"Updated: {format_timestamp(item.published_at)}"
        )

    return "\n".join(lines)
