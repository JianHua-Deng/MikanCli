from __future__ import annotations

from mikancli.cli.input_parsing import prompt_required_text
from mikancli.cli.prompts import select_option
from mikancli.core.models import MikanBangumi, MikanSubgroup, SearchRequest
from mikancli.core.normalize import collapse_spaces
from mikancli.display import build_feed_preview_text
from mikancli.integrations.mikan import (
    MikanLookupError,
    fetch_mikan_feed_items,
    fetch_mikan_subgroups,
    search_mikan_bangumi,
)

SEARCH_AGAIN = "__search_again__"
BACK_TO_CANDIDATES = "__back_to_candidates__"
BACK_TO_SUBGROUPS = "__back_to_subgroups__"
CONFIRM_SUBGROUP = "__confirm_subgroup__"
REJECT_SUBGROUP = "__reject_subgroup__"


def _search_prompt(*, retry: bool = False) -> str:
    prefix = "Enter another anime title or search keyword" if retry else "Enter anime title or search keyword"
    return f"{prefix} (or type 'exit' to quit): "


def select_candidate_or_search_again(
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
        allow_exit=True,
    )
    if selected == SEARCH_AGAIN:
        return SEARCH_AGAIN
    return candidates[selected]


def select_subgroup_or_navigate(
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
        allow_exit=True,
    )
    if selected == BACK_TO_CANDIDATES:
        return BACK_TO_CANDIDATES
    if selected == SEARCH_AGAIN:
        return SEARCH_AGAIN
    return subgroups[selected]


def confirm_subgroup_selection(preview_text: str) -> str:
    return select_option(
        f"Use this subgroup feed?\n\n{preview_text}",
        [
            (CONFIRM_SUBGROUP, "Yes"),
            (REJECT_SUBGROUP, "No, search with different words"),
            (BACK_TO_SUBGROUPS, "Back to subgroup list"),
        ],
        default=CONFIRM_SUBGROUP,
        allow_exit=True,
    )


def resolve_mikan_selection(
    request: SearchRequest,
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


def run_interactive_selection(
    *,
    initial_keyword: str | None,
) -> tuple[MikanBangumi, MikanSubgroup]:
    keyword = collapse_spaces(initial_keyword or "")
    if not keyword:
        keyword = prompt_required_text(_search_prompt())

    while True:
        try:
            candidates = search_mikan_bangumi(keyword)
        except MikanLookupError as exc:
            print(str(exc))
            keyword = prompt_required_text(_search_prompt(retry=True))
            continue

        if not candidates:
            print(f"No Mikan results found for '{keyword}'.")
            keyword = prompt_required_text(_search_prompt(retry=True))
            continue

        selected_candidate = select_candidate_or_search_again(candidates, keyword=keyword)
        if selected_candidate == SEARCH_AGAIN:
            keyword = prompt_required_text(_search_prompt(retry=True))
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

            selected_subgroup = select_subgroup_or_navigate(
                subgroups,
                bangumi_title=bangumi.title,
            )

            if selected_subgroup == BACK_TO_CANDIDATES:
                break
            if selected_subgroup == SEARCH_AGAIN:
                keyword = prompt_required_text(_search_prompt(retry=True))
                break

            subgroup = selected_subgroup

            try:
                feed_items = fetch_mikan_feed_items(subgroup.feed_url)
            except MikanLookupError as exc:
                print(str(exc))
                continue

            preview_text = build_feed_preview_text(subgroup, feed_items)
            decision = confirm_subgroup_selection(preview_text)
            if decision == BACK_TO_SUBGROUPS:
                continue
            if decision == REJECT_SUBGROUP:
                keyword = prompt_required_text(_search_prompt(retry=True))
                break

            return bangumi, subgroup
