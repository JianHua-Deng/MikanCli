from __future__ import annotations

from mikancli.cli.input_parsing import prompt_required_text
from mikancli.cli.prompts import select_option
from mikancli.core.models import MikanBangumi, MikanSubgroup, SearchRequest
from mikancli.core.normalize import collapse_spaces
from mikancli.display import build_feed_preview_text
from mikancli.i18n import t
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


def search_prompt(*, retry: bool = False) -> str:
    return t("search.prompt_retry" if retry else "search.prompt")


def select_candidate_or_search_again(candidates: tuple[MikanBangumi, ...], *, keyword: str) -> MikanBangumi | str:

    options: list[tuple[int | str, str]] = [
        (index, f"{candidate.title} (Bangumi {candidate.bangumi_id})")
        for index, candidate in enumerate(candidates)
    ]
    options.append((SEARCH_AGAIN, t("search.search_again")))

    selected = select_option(
        t("search.choose_candidate", keyword=keyword),
        options,
        default=0,
        allow_exit=True,
        separator_before_values=(SEARCH_AGAIN,),
        separator_before_exit=False,
    )
    if selected == SEARCH_AGAIN:
        return SEARCH_AGAIN
    return candidates[selected]


def select_subgroup_or_navigate(subgroups: tuple[MikanSubgroup, ...], *, bangumi_title: str) -> MikanSubgroup | str:
    """Ask the user to choose a subgroup RSS feed or navigate back through the search flow. Returns a MikanSubgroup, BACK_TO_CANDIDATES, or SEARCH_AGAIN based on the user's decision."""

    options: list[tuple[int | str, str]] = [
        (index, f"{subgroup.title} (Subgroup {subgroup.subgroup_id})")
        for index, subgroup in enumerate(subgroups)
    ]
    options.extend(
        [
            (BACK_TO_CANDIDATES, t("search.back_to_candidates")),
            (SEARCH_AGAIN, t("search.search_again")),
        ]
    )

    selected = select_option(
        t("search.choose_subgroup", title=bangumi_title),
        options,
        default=0,
        allow_exit=True,
        separator_before_values=(BACK_TO_CANDIDATES,),
        separator_before_exit=False,
    )
    if selected == BACK_TO_CANDIDATES:
        return BACK_TO_CANDIDATES
    if selected == SEARCH_AGAIN:
        return SEARCH_AGAIN
    return subgroups[selected]


def confirm_subgroup_selection(preview_text: str) -> str:
    """Show a feed preview and ask whether to use that subgroup feed. Returns CONFIRM_SUBGROUP, REJECT_SUBGROUP, or BACK_TO_SUBGROUPS based on the user's decision"""
    print(preview_text)
    return select_option(
        t("search.use_subgroup"),
        [
            (CONFIRM_SUBGROUP, t("common.yes")),
            (REJECT_SUBGROUP, t("search.no_search_again")),
            (BACK_TO_SUBGROUPS, t("search.back_to_subgroups")),
        ],
        default=CONFIRM_SUBGROUP,
        allow_exit=True,
        separator_before_values=(BACK_TO_SUBGROUPS,),
        separator_before_exit=False,
    )


def resolve_mikan_selection(request: SearchRequest,) -> tuple[MikanBangumi | None, MikanSubgroup | None, tuple[str, ...]]:
    """Resolve the first matching Bangumi and subgroup for non-interactive JSON mode. Returns optional selected objects plus notes describing missing data or JSON-mode limitations"""

    try:
        candidates = search_mikan_bangumi(request.keyword)
    except MikanLookupError as exc:
        return None, None, (str(exc), t("search.json_preview_note"))

    if not candidates:
        return (
            None,
            None,
            (
                t("search.no_matching_json"),
                t("search.json_preview_note"),
            ),
        )

    selected_bangumi = candidates[0]

    try:
        subgroups = fetch_mikan_subgroups(selected_bangumi.bangumi_id)
    except MikanLookupError as exc:
        return (
            selected_bangumi,
            None,
            (str(exc), t("search.json_preview_note")),
        )

    if not subgroups:
        return (
            selected_bangumi,
            None,
            (
                t("search.no_subgroup_json"),
                t("search.json_preview_note"),
            ),
        )

    return selected_bangumi, subgroups[0], (t("search.json_preview_note"),)


def run_interactive_selection(*, initial_keyword: str | None) -> tuple[MikanBangumi, MikanSubgroup]:
    """Run Mikan search, Bangumi selection, subgroup selection, and feed preview loop. Returns the confirmed Bangumi and subgroup, or propagates ExitRequested when the user quits"""
    
    keyword = collapse_spaces(initial_keyword or "")
    if not keyword:
        keyword = prompt_required_text(search_prompt())

    while True:
        try:
            candidates = search_mikan_bangumi(keyword)
        except MikanLookupError as exc:
            print(str(exc))
            keyword = prompt_required_text(search_prompt(retry=True))
            continue

        if not candidates:
            print(t("search.no_results", keyword=keyword))
            keyword = prompt_required_text(search_prompt(retry=True))
            continue

        selected_candidate = select_candidate_or_search_again(candidates, keyword=keyword)
        if selected_candidate == SEARCH_AGAIN:
            keyword = prompt_required_text(search_prompt(retry=True))
            continue

        bangumi = selected_candidate

        while True:
            try:
                subgroups = fetch_mikan_subgroups(bangumi.bangumi_id)
            except MikanLookupError as exc:
                print(str(exc))
                break

            if not subgroups:
                print(t("search.no_subgroup"))
                break

            selected_subgroup = select_subgroup_or_navigate(
                subgroups,
                bangumi_title=bangumi.title,
            )

            if selected_subgroup == BACK_TO_CANDIDATES:
                break
            if selected_subgroup == SEARCH_AGAIN:
                keyword = prompt_required_text(search_prompt(retry=True))
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
                keyword = prompt_required_text(search_prompt(retry=True))
                break

            return bangumi, subgroup
