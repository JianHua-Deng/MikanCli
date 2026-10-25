from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from datetime import datetime

from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from mikancli.core.models import MikanFeedItem, MikanSubgroup, RuleDraft
from mikancli.i18n import t

PRIMARY_COLOR = "#ffb454"
FEED_PREVIEW_PAGE_SIZE = 12
console = Console(
    markup=False, highlight=False, emoji=False,
    theme=Theme({
        "heading": f"bold {PRIMARY_COLOR}", "label": PRIMARY_COLOR, "note": "dim",
        "success": "green", "warning": "yellow", "error": "bold red",
    }),
)


def print_message(message: str, *, style: str = "note") -> None:
    """Print literal feedback with wrapping in terminals and plain redirected text."""
    console.print(Text(message), style=style, soft_wrap=not console.is_terminal)


def print_section(title: str, *paragraphs: str) -> None:
    """Give each interactive stage a wrapping heading and optional context."""
    content = Text()
    content.append(title, style="heading")
    for paragraph in paragraphs:
        content.append("\n\n" + paragraph)
    console.print()
    if console.is_terminal:
        console.print(Panel(content, border_style="heading", padding=(0, 1),
                            width=min(console.width, 100)))
    else:
        console.print(content, soft_wrap=True)


def loading(message: str) -> AbstractContextManager[object]:
    """Animate terminal requests, or print one static message when redirected."""
    if console.is_terminal and console.is_interactive:
        return console.status(Text(message), spinner="dots", spinner_style=PRIMARY_COLOR)
    print_message(message)
    return nullcontext()


def print_text_summary(draft: RuleDraft) -> int:
    """Print a human-readable summary of a rule draft. Returns 0 after writing the summary and any next-step notes to stdout."""
    fields = {
        "keyword": draft.keyword,
        "normalized_keyword": draft.normalized_keyword,
        "rule_name": draft.rule_name,
        "mikan_title": draft.mikan_title or t("common.not_found"),
        "mikan_subgroup": draft.mikan_subgroup or t("common.not_found"),
        "mikan_page": draft.mikan_page_url or t("common.not_found"),
        "feed_url": draft.feed_url or t("common.not_found"),
        "must_contain": ", ".join(draft.must_contain) or t("common.none"),
        "must_not_contain": ", ".join(draft.must_not_contain) or t("common.none"),
        "min_episode": draft.min_episode if draft.min_episode is not None else t("common.none"),
        "save_path": draft.save_path or t("common.not_set"),
    }
    table = Table.grid(padding=(0, 2))
    table.add_column(style="label")
    table.add_column(overflow="fold")
    for key, value in fields.items():
        if console.is_terminal and key in {"must_contain", "save_path"}:
            table.add_row()
        table.add_row(Text(t(f"display.{key}", value="").rstrip()), Text(str(value)))
    console.print()
    heading = Text(t("display.rule_header").strip("- "))
    if console.is_terminal:
        console.print(Panel(table, title=heading, border_style="heading",
                            padding=(1, 2), width=min(console.width, 100)))
    else:
        console.rule(heading, style="heading")
        console.print(table)
    console.print()
    for note in draft.notes:
        console.print(Text(t("display.next_step", value=note)), style="note")

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
    return build_feed_preview_page_text(
        subgroup,
        feed_items,
        page=1,
        page_size=max(len(feed_items), 1),
    )


def print_feed_preview_page(
    subgroup: MikanSubgroup,
    feed_items: tuple[MikanFeedItem, ...],
    *,
    page: int,
) -> None:
    """Render a feed page with literal titles and wrapping terminal output."""
    content = build_feed_preview_page_text(subgroup, feed_items, page=page)
    if not console.is_terminal:
        console.print(Text(content), soft_wrap=True)
        return

    sections = []
    for index, line in enumerate(content.splitlines()):
        if not line:
            sections.append(Rule(style="note"))
            continue
        if line.startswith("   "):
            details = Text(line.lstrip())
            if details.cell_len <= min(console.width, 100) - 8:
                sections.append(Rule(details, align="left", style="note"))
            else:
                sections.append(details)
            continue
        style = "heading" if index == 0 else "bold" if index >= 4 else ""
        sections.append(Text(line, style=style))
    console.print()
    console.print(Panel(Group(*sections), border_style="heading",
                        padding=(0, 1), width=min(console.width, 100)))


def build_feed_preview_page_text(
    subgroup: MikanSubgroup,
    feed_items: tuple[MikanFeedItem, ...],
    *,
    page: int,
    page_size: int = FEED_PREVIEW_PAGE_SIZE,
) -> str:
    """Build one page of RSS feed preview text."""
    total_items = len(feed_items)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    current_page = min(max(page, 1), total_pages)
    start_index = (current_page - 1) * page_size
    end_index = min(start_index + page_size, total_items)

    lines = [
        t("display.feed_preview", title=subgroup.title),
        t("display.feed_url_plain", url=subgroup.feed_url),
        t(
            "display.items_page",
            count=total_items,
            page=current_page,
            pages=total_pages,
        ),
        "",
    ]

    if not feed_items:
        lines.append(t("display.feed_empty"))
        return "\n".join(lines)

    for index, item in enumerate(
        feed_items[start_index:end_index],
        start=start_index + 1,
    ):
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
