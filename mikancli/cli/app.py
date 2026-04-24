from __future__ import annotations

import argparse
import json
from pathlib import Path

from mikancli.bootstrap import ensure_runtime_dependencies
from mikancli.cli.input_helpers import parse_word_list
from mikancli.cli.interactive import resolve_mikan_selection, run_interactive_selection
from mikancli.cli.prompts import (
    ExitRequested,
    confirm_choice,
    prompt_password,
    prompt_text,
    select_option,
)
from mikancli.config import (
    get_config_path,
    get_system_downloads_path,
    load_config,
    pick_directory,
    save_config,
)
from mikancli.core.models import AppConfig, QBittorrentSettings, RuleDraft, SearchRequest
from mikancli.core.normalize import collapse_spaces
from mikancli.core.rules import build_rule_draft
from mikancli.display import print_text_summary
from mikancli.integrations.qbittorrent import (
    QBittorrentError,
    check_connection,
    normalize_qbittorrent_url,
)

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


def _should_save_as_default(selected_path: str, config: AppConfig) -> bool:
    if config.default_save_path == selected_path:
        return False

    return confirm_choice(
        f"Save '{selected_path}' as the default download folder for future runs?",
        default=True,
        allow_exit=True,
    )


def _prompt_for_manual_save_path() -> str | None:
    entered = collapse_spaces(
        prompt_text("Enter a download folder path", allow_exit=True)
    )
    return entered or None


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


def _setup_qbittorrent(config: AppConfig, config_path: Path) -> int:
    print()
    print("----- qBittorrent setup instructions -----")
    print("1. Open qBittorrent settings.")
    print("2. Enable WebUI / remote control if it is not enabled yet.")
    print("3. Copy the WebUI address, username, and password from qBittorrent.")
    print("4. Input those values into the prompts below.")
    print("5. After successful verification, the values will be saved to the config file for future runs.")
    print("------------------------------------------")
    print()

    default_url = config.qbittorrent_url or "http://localhost:8080"
    entered_url = (
        collapse_spaces(
            prompt_text(
                "Enter qBittorrent WebUI URL (press Enter for http://localhost:8080 - this is usually the default URL unless you tweeked it in qBittorrent settings)",
                default=default_url,
                allow_exit=True,
            )
        )
        or "http://localhost:8080"
    )

    print()
    print(f"Bypass authentication for clients on localhost? If you have this enabled in qBittorrent settings, you can just press Enter for the next two prompts.")
    username = (
        collapse_spaces(
            prompt_text(
                "Enter qBittorrent WebUI username ( press Enter to leave blank)",
                default=config.qbittorrent_username or "",
                allow_exit=True,
            )
        )
        or None
    )
    password = prompt_password(
        "Enter qBittorrent WebUI password (press Enter to leave blank)",
        allow_exit=True,
    ) or None

    settings = QBittorrentSettings(
        url=entered_url,
        username=username,
        password=password,
    )

    try:
        print("Verifying qBittorrent connection...")
        version = check_connection(settings)
    except QBittorrentError as exc:
        print(str(exc))
        return 1

    save_config(
        config_path,
        AppConfig(
            default_save_path=config.default_save_path,
            qbittorrent_url=normalize_qbittorrent_url(entered_url),
            qbittorrent_username=username,
            qbittorrent_password=password,
        ),
    )
    print(
        "qBittorrent connection verified successfully "
        f"(version: {version})."
    )
    return 0


def _maybe_run_qbittorrent_setup(config: AppConfig, config_path: Path) -> int:
    if config.qbittorrent_url:
        return 0

    should_setup = confirm_choice(
        "qBittorrent is not set up yet. Set up qBittorrent WebUI now?",
        default=True,
        allow_exit=True,
    )
    if not should_setup:
        return 0

    while True:
        exit_code = _setup_qbittorrent(config, config_path)
        if exit_code == 0:
            return 0

        continue_without_setup = confirm_choice(
            "Continue without qBittorrent setup for now?",
            default=False,
            allow_exit=True,
        )
        if continue_without_setup:
            return 0


def _run_qbittorrent_configuration_route(config: AppConfig, config_path: Path) -> int:
    while True:
        exit_code = _setup_qbittorrent(config, config_path)
        if exit_code == 0:
            return 0

        retry_setup = confirm_choice(
            "Retry qBittorrent setup?",
            default=True,
            allow_exit=True,
        )
        if not retry_setup:
            return 1


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
            allow_exit=True,
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
            save_config(
                config_path,
                AppConfig(
                    default_save_path=selected_path,
                    qbittorrent_url=config.qbittorrent_url,
                    qbittorrent_username=config.qbittorrent_username,
                    qbittorrent_password=config.qbittorrent_password,
                ),
            )

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

        setup_exit_code = _maybe_run_qbittorrent_setup(config, config_path)
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
