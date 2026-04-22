from __future__ import annotations

import argparse
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
from autofeedsync.display import print_text_summary
from autofeedsync.input_helpers import parse_word_list
from autofeedsync.interactive import resolve_mikan_selection, run_interactive_selection
from autofeedsync.models import AppConfig, RuleDraft, SearchRequest
from autofeedsync.normalize import collapse_spaces
from autofeedsync.prompts import confirm_choice, prompt_text, select_option
from autofeedsync.rules import build_rule_draft


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


def _prompt_word_list(prompt: str) -> tuple[str, ...]:
    entered = collapse_spaces(prompt_text(prompt))
    if not entered:
        return ()

    return parse_word_list(entered)


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

        bangumi, subgroup, lookup_notes = resolve_mikan_selection(request)
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
    return print_text_summary(draft)
