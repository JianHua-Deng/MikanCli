from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path

from autofeedsync.bootstrap import ensure_runtime_dependencies
from autofeedsync.config import (
    get_config_path,
    get_system_downloads_path,
    load_config,
    pick_directory,
    save_config,
)
from autofeedsync.mikan import (
    MikanLookupError,
    fetch_mikan_feed_items,
    fetch_mikan_subgroups,
    search_mikan_bangumi,
)
from autofeedsync.models import (
    AppConfig,
    MikanBangumi,
    MikanFeedItem,
    MikanSubgroup,
    RuleDraft,
    SearchRequest,
)
from autofeedsync.normalize import collapse_spaces
from autofeedsync.prompts import confirm_choice, prompt_text, select_option
from autofeedsync.rules import build_rule_draft

SEARCH_AGAIN = "__search_again__"
BACK_TO_CANDIDATES = "__back_to_candidates__"
BACK_TO_SUBGROUPS = "__back_to_subgroups__"
CONFIRM_SUBGROUP = "__confirm_subgroup__"
REJECT_SUBGROUP = "__reject_subgroup__"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autofeedsync",
        description=(
            "Search Mikan for an anime, inspect subgroup RSS contents, and preview "
            "the qBittorrent rule inputs."
        ),
    )
    parser.add_argument("keyword", nargs="?", help="Anime title or search phrase.")
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Word that must appear in accepted releases. Repeat for multiple values.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Word that must not appear in accepted releases. Repeat for multiple values.",
    )
    parser.add_argument(
        "--save-path",
        help="Optional save path to attach to the future qBittorrent rule.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the draft as JSON.",
    )
    return parser


def _print_text_summary(draft: RuleDraft) -> int:
    print("AutoFeedSync draft")
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
    print()
    for note in draft.notes:
        print(f"Next step: {note}")

    return 0


def _prompt_required_text(prompt: str) -> str:
    while True:
        entered = collapse_spaces(prompt_text(prompt))
        if entered:
            return entered
        print("A value is required.")


def _parse_word_list(value: str) -> tuple[str, ...]:
    words: list[str] = []
    seen: set[str] = set()

    for raw_part in value.split(","):
        cleaned = collapse_spaces(raw_part)
        if not cleaned:
            continue

        marker = cleaned.casefold()
        if marker in seen:
            continue

        seen.add(marker)
        words.append(cleaned)

    return tuple(words)


def _prompt_word_list(prompt: str) -> tuple[str, ...]:
    entered = collapse_spaces(prompt_text(prompt))
    if not entered:
        return ()

    return _parse_word_list(entered)


def _should_save_as_default(selected_path: str, config: AppConfig) -> bool:
    if config.default_save_path == selected_path:
        return False

    return confirm_choice(
        f"Save '{selected_path}' as the default download folder for future runs?",
        default=True,
    )


def _prompt_for_manual_save_path() -> str | None:
    entered = collapse_spaces(prompt_text("Enter a download folder path"))
    return entered or None


def _prompt_for_save_path(config: AppConfig, config_path: Path) -> str:
    downloads_path = get_system_downloads_path()
    menu_options: list[tuple[str, str]] = []

    if config.default_save_path:
        menu_options.append(("saved-default", f"Use saved default: {config.default_save_path}"))
    menu_options.append(("downloads", f"Use Downloads folder: {downloads_path}"))
    menu_options.append(("browse", "Browse for folder"))
    menu_options.append(("manual", "Type folder path manually"))

    while True:
        selected_key = select_option(
            "Choose a download folder option",
            menu_options,
            default=menu_options[0][0],
        )

        if selected_key == "saved-default":
            return config.default_save_path or downloads_path

        if selected_key == "downloads":
            selected_path = downloads_path
        elif selected_key == "browse":
            selected_path = pick_directory(
                initial_dir=config.default_save_path or downloads_path
            )
            if not selected_path:
                print("No folder was selected. Choose another option.")
                continue
        else:
            selected_path = _prompt_for_manual_save_path()
            if not selected_path:
                print("No path was entered. Choose another option.")
                continue

        if _should_save_as_default(selected_path, config):
            save_config(config_path, AppConfig(default_save_path=selected_path))

        return selected_path


def _format_size(size_bytes: int | None) -> str:
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


def _format_timestamp(value: str | None) -> str:
    if not value:
        return "(unknown)"

    try:
        return datetime.fromisoformat(value).strftime("%Y/%m/%d %H:%M")
    except ValueError:
        return value


def _print_feed_preview(subgroup: MikanSubgroup, feed_items: tuple[MikanFeedItem, ...]) -> None:
    print()
    print(f"Subgroup preview: {subgroup.title}")
    print(f"Feed URL: {subgroup.feed_url}")
    print(f"Items: {len(feed_items)}")
    print()

    if not feed_items:
        print("(The RSS feed is empty.)")
        print()
        return

    for index, item in enumerate(feed_items, start=1):
        print(f"{index}. {item.title}")
        print(
            "   "
            f"Size: {_format_size(item.content_length)} | "
            f"Updated: {_format_timestamp(item.published_at)}"
        )
    print()


def _select_candidate_or_search_again(
    candidates: tuple[MikanBangumi, ...],
    *,
    keyword: str,
) -> MikanBangumi | str:
    options: list[tuple[int | str, str]] = [
        (index, f"{candidate.title} (Bangumi {candidate.bangumi_id})")
        for index, candidate in enumerate(candidates)
    ]
    options.append((SEARCH_AGAIN, "Search with different words"))

    selected = select_option(
        f"Choose the Mikan entry for '{keyword}'",
        options,
        default=0,
    )
    if selected == SEARCH_AGAIN:
        return SEARCH_AGAIN
    return candidates[selected]


def _select_subgroup_or_navigate(
    subgroups: tuple[MikanSubgroup, ...],
    *,
    bangumi_title: str,
) -> MikanSubgroup | str:
    options: list[tuple[int | str, str]] = [
        (index, f"{subgroup.title} (Subgroup {subgroup.subgroup_id})")
        for index, subgroup in enumerate(subgroups)
    ]
    options.extend(
        [
            (BACK_TO_CANDIDATES, "Back to Bangumi list"),
            (SEARCH_AGAIN, "Search with different words"),
        ]
    )

    selected = select_option(
        f"Choose the subgroup for '{bangumi_title}'",
        options,
        default=0,
    )
    if selected == BACK_TO_CANDIDATES:
        return BACK_TO_CANDIDATES
    if selected == SEARCH_AGAIN:
        return SEARCH_AGAIN
    return subgroups[selected]


def _confirm_subgroup_selection() -> str:
    return select_option(
        "Use this subgroup feed?",
        [
            (CONFIRM_SUBGROUP, "Yes"),
            (REJECT_SUBGROUP, "No, search with different words"),
            (BACK_TO_SUBGROUPS, "Back to subgroup list"),
        ],
        default=CONFIRM_SUBGROUP,
    )


def resolve_save_path(
    cli_save_path: str | None,
    config: AppConfig,
    *,
    prompt_for_default: bool,
    config_path: Path,
) -> str | None:
    if cli_save_path:
        return collapse_spaces(cli_save_path)

    if not prompt_for_default:
        return config.default_save_path or get_system_downloads_path()

    return _prompt_for_save_path(config, config_path)


def build_request_from_args(
    args: argparse.Namespace,
    *,
    config: AppConfig,
    config_path: Path,
) -> SearchRequest:
    if not args.keyword:
        raise ValueError("keyword is required when using --json")

    save_path = resolve_save_path(
        args.save_path,
        config,
        prompt_for_default=False,
        config_path=config_path,
    )

    return SearchRequest(
        keyword=collapse_spaces(args.keyword),
        include_words=tuple(args.include),
        exclude_words=tuple(args.exclude),
        save_path=save_path,
    )


def resolve_mikan_selection(
    request: SearchRequest,
    *,
    interactive: bool,
) -> tuple[MikanBangumi | None, MikanSubgroup | None, tuple[str, ...]]:
    try:
        candidates = search_mikan_bangumi(request.keyword)
    except MikanLookupError as exc:
        return None, None, (str(exc), "qBittorrent submission not implemented yet.")

    if not candidates:
        return (
            None,
            None,
            (
                "No matching Mikan Bangumi entry was found for the keyword.",
                "qBittorrent submission not implemented yet.",
            ),
        )

    selected_bangumi = candidates[0]

    try:
        subgroups = fetch_mikan_subgroups(selected_bangumi.bangumi_id)
    except MikanLookupError as exc:
        return (
            selected_bangumi,
            None,
            (str(exc), "qBittorrent submission not implemented yet."),
        )

    if not subgroups:
        return (
            selected_bangumi,
            None,
            (
                "No subgroup-specific RSS feed was found for the selected Bangumi.",
                "qBittorrent submission not implemented yet.",
            ),
        )

    return selected_bangumi, subgroups[0], ("qBittorrent submission not implemented yet.",)


def _run_interactive_selection(
    *,
    initial_keyword: str | None,
) -> tuple[MikanBangumi, MikanSubgroup]:
    keyword = collapse_spaces(initial_keyword or "")
    if not keyword:
        keyword = _prompt_required_text("Enter anime title or search keyword: ")

    while True:
        try:
            candidates = search_mikan_bangumi(keyword)
        except MikanLookupError as exc:
            print(str(exc))
            keyword = _prompt_required_text("Enter another anime title or search keyword: ")
            continue

        if not candidates:
            print(f"No Mikan results found for '{keyword}'.")
            keyword = _prompt_required_text("Enter another anime title or search keyword: ")
            continue

        selected_candidate = _select_candidate_or_search_again(candidates, keyword=keyword)
        if selected_candidate == SEARCH_AGAIN:
            keyword = _prompt_required_text("Enter another anime title or search keyword: ")
            continue

        bangumi = selected_candidate

        while True:
            try:
                subgroups = fetch_mikan_subgroups(bangumi.bangumi_id)
            except MikanLookupError as exc:
                print(str(exc))
                break

            if not subgroups:
                print("No subgroup-specific RSS feed was found for the selected Bangumi.")
                break

            selected_subgroup = _select_subgroup_or_navigate(
                subgroups,
                bangumi_title=bangumi.title,
            )

            if selected_subgroup == BACK_TO_CANDIDATES:
                break
            if selected_subgroup == SEARCH_AGAIN:
                keyword = _prompt_required_text("Enter another anime title or search keyword: ")
                break

            subgroup = selected_subgroup

            try:
                feed_items = fetch_mikan_feed_items(subgroup.feed_url)
            except MikanLookupError as exc:
                print(str(exc))
                continue

            _print_feed_preview(subgroup, feed_items)
            decision = _confirm_subgroup_selection()
            if decision == BACK_TO_SUBGROUPS:
                continue
            if decision == REJECT_SUBGROUP:
                keyword = _prompt_required_text("Enter another anime title or search keyword: ")
                break

            return bangumi, subgroup


def _build_interactive_draft(
    args: argparse.Namespace,
    *,
    config: AppConfig,
    config_path: Path,
) -> RuleDraft:
    bangumi, subgroup = _run_interactive_selection(initial_keyword=args.keyword)

    include_words = tuple(args.include) or _prompt_word_list(
        "Enter include words separated by commas, or press Enter to skip: "
    )
    exclude_words = tuple(args.exclude) or _prompt_word_list(
        "Enter exclude words separated by commas, or press Enter to skip: "
    )
    save_path = resolve_save_path(
        args.save_path,
        config,
        prompt_for_default=True,
        config_path=config_path,
    )

    request = SearchRequest(
        keyword=bangumi.title,
        include_words=include_words,
        exclude_words=exclude_words,
        save_path=save_path,
    )
    return build_rule_draft(
        request,
        bangumi=bangumi,
        subgroup=subgroup,
        notes=("qBittorrent submission not implemented yet.",),
    )


def main(argv: list[str] | None = None) -> int:
    ensure_runtime_dependencies()

    parser = build_parser()
    args = parser.parse_args(argv)
    config_path = get_config_path()
    config = load_config(config_path)

    if args.json:
        try:
            request = build_request_from_args(
                args,
                config=config,
                config_path=config_path,
            )
        except ValueError as exc:
            parser.error(str(exc))

        bangumi, subgroup, lookup_notes = resolve_mikan_selection(
            request,
            interactive=False,
        )
        draft = build_rule_draft(
            request,
            bangumi=bangumi,
            subgroup=subgroup,
            notes=lookup_notes,
        )
        print(json.dumps(draft.to_dict(), ensure_ascii=False, indent=2))
        return 0

    draft = _build_interactive_draft(
        args,
        config=config,
        config_path=config_path,
    )
    return _print_text_summary(draft)
