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
from autofeedsync.models import AppConfig
from autofeedsync.models import SearchRequest
from autofeedsync.normalize import collapse_spaces
from autofeedsync.prompts import confirm_choice, prompt_text, select_option
from autofeedsync.rules import build_rule_draft


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autofeedsync",
        description=(
            "Prepare a draft qBittorrent RSS rule from an anime keyword. "
            "This first increment only builds and previews the rule inputs."
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
        "--group",
        help="Preferred release group to include in the rule draft.",
    )
    parser.add_argument(
        "--resolution",
        help="Preferred resolution to include in the rule draft, such as 1080p.",
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


def _print_text_summary(request: SearchRequest) -> int:
    draft = build_rule_draft(request)

    print("AutoFeedSync draft")
    print(f"Keyword: {draft.keyword}")
    print(f"Normalized keyword: {draft.normalized_keyword}")
    print(f"Rule name: {draft.rule_name}")
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


def _prompt_optional_text(prompt: str) -> str | None:
    entered = collapse_spaces(prompt_text(prompt))
    return entered or None


def _prompt_resolution() -> str | None:
    options = [
        ("skip", "Skip resolution preference"),
        ("1080p", "Use 1080p"),
        ("720p", "Use 720p"),
        ("2160p", "Use 2160p / 4K"),
        ("manual", "Type resolution manually"),
    ]

    while True:
        selected_key = select_option(
            "Choose a resolution preference",
            options,
            default="skip",
        )

        if selected_key == "skip":
            return None
        if selected_key == "manual":
            entered = _prompt_optional_text(
                "Enter a resolution value such as 1080p, or press Enter to skip: "
            )
            if entered:
                return entered
            continue

        return selected_key


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
    interactive = not args.json

    if args.keyword:
        keyword = collapse_spaces(args.keyword)
    elif interactive:
        keyword = _prompt_required_text("Enter anime title or search keyword: ")
    else:
        raise ValueError("keyword is required when using --json")

    if args.group is not None:
        group = collapse_spaces(args.group) or None
    elif interactive:
        group = _prompt_optional_text(
            "Enter preferred release group, or press Enter to skip: "
        )
    else:
        group = None

    if args.resolution is not None:
        resolution = collapse_spaces(args.resolution) or None
    elif interactive:
        resolution = _prompt_resolution()
    else:
        resolution = None

    include_words = tuple(args.include)
    if not include_words and interactive:
        include_words = _prompt_word_list(
            "Enter include words separated by commas, or press Enter to skip: "
        )

    exclude_words = tuple(args.exclude)
    if not exclude_words and interactive:
        exclude_words = _prompt_word_list(
            "Enter exclude words separated by commas, or press Enter to skip: "
        )

    save_path = resolve_save_path(
        args.save_path,
        config,
        prompt_for_default=interactive,
        config_path=config_path,
    )

    return SearchRequest(
        keyword=keyword,
        include_words=include_words,
        exclude_words=exclude_words,
        group=group,
        resolution=resolution,
        save_path=save_path,
    )


def main(argv: list[str] | None = None) -> int:
    ensure_runtime_dependencies()

    parser = build_parser()
    args = parser.parse_args(argv)
    config_path = get_config_path()
    config = load_config(config_path)
    try:
        request = build_request_from_args(
            args,
            config=config,
            config_path=config_path,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if args.json:
        print(json.dumps(build_rule_draft(request).to_dict(), indent=2))
        return 0

    return _print_text_summary(request)
