from __future__ import annotations

import argparse
import json
from pathlib import Path

from mikancli.bootstrap import ensure_runtime_dependencies
from mikancli.cli.input_parsing import parse_word_list
from mikancli.cli.prompts import ExitRequested, prompt_text, select_option
from mikancli.cli.qbittorrent_flow import (
    _prompt_for_qbittorrent_setup_if_needed,
    _run_qbittorrent_configuration_route,
    _setup_qbittorrent,
)
from mikancli.cli.save_path_flow import (
    _build_content_save_path,
    _prompt_for_content_folder_name,
    _prompt_for_save_path,
    resolve_save_path,
)
from mikancli.cli.search_flow import resolve_mikan_selection, run_interactive_selection
from mikancli.config import get_config_path, load_config
from mikancli.core.models import AppConfig, RuleDraft, SearchRequest
from mikancli.core.normalize import collapse_spaces
from mikancli.core.rules import build_rule_draft
from mikancli.display import print_text_summary

STARTUP_ACTION_SEARCH = "search"
STARTUP_ACTION_QBITTORRENT = "qbittorrent"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mikancli",
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
    parser.add_argument(
        "--setup-qbittorrent",
        action="store_true",
        help="Configure and verify qBittorrent WebUI access.",
    )
    return parser


def _prompt_word_list(prompt: str) -> tuple[str, ...]:
    entered = collapse_spaces(prompt_text(prompt, allow_exit=True))
    if not entered:
        return ()

    return parse_word_list(entered)


def _prompt_startup_action() -> str:
    return select_option(
        "Choose what you want to do",
        [
            (STARTUP_ACTION_SEARCH, "Search anime"),
            (STARTUP_ACTION_QBITTORRENT, "Modify qBittorrent configurations"),
        ],
        default=STARTUP_ACTION_SEARCH,
        allow_exit=True,
    )


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


def _build_interactive_draft(
    args: argparse.Namespace,
    *,
    config: AppConfig,
    config_path: Path,
) -> RuleDraft:
    bangumi, subgroup = run_interactive_selection(initial_keyword=args.keyword)

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
    content_folder_name = _prompt_for_content_folder_name(bangumi.title)
    final_save_path = _build_content_save_path(save_path, content_folder_name)

    request = SearchRequest(
        keyword=bangumi.title,
        include_words=include_words,
        exclude_words=exclude_words,
        save_path=final_save_path,
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

    if args.setup_qbittorrent:
        try:
            return _setup_qbittorrent(config, config_path)
        except ExitRequested:
            print("Exited MikanCli.")
            return 0

    if args.json:
        try:
            request = build_request_from_args(
                args,
                config=config,
                config_path=config_path,
            )
        except ValueError as exc:
            parser.error(str(exc))

        bangumi, subgroup, lookup_notes = resolve_mikan_selection(request)
        draft = build_rule_draft(
            request,
            bangumi=bangumi,
            subgroup=subgroup,
            notes=lookup_notes,
        )
        print(json.dumps(draft.to_dict(), ensure_ascii=False, indent=2))
        return 0

    try:
        if args.keyword is None:
            startup_action = _prompt_startup_action()
            if startup_action == STARTUP_ACTION_QBITTORRENT:
                return _run_qbittorrent_configuration_route(config, config_path)

        setup_exit_code = _prompt_for_qbittorrent_setup_if_needed(
            config,
            config_path,
        )
        if setup_exit_code != 0:
            return setup_exit_code
        draft = _build_interactive_draft(
            args,
            config=config,
            config_path=config_path,
        )
    except ExitRequested:
        print("Exited MikanCli.")
        return 0

    return print_text_summary(draft)
