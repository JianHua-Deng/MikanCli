from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from mikancli import __version__
from mikancli.cli.input_parsing import prompt_word_list
from mikancli.cli.prompts import ExitRequested, select_option
from mikancli.cli.qbittorrent_flow import (
    QBITTORRENT_SETUP_SUCCESS,
    QBITTORRENT_NOT_CONFIGURED,
    QBITTORRENT_SUBMISSION_SKIPPED,
    prompt_for_qbittorrent_setup_if_needed,
    prompt_to_submit_rule_to_qbittorrent,
    run_qbittorrent_configuration_flow,
    setup_qbittorrent,
)
from mikancli.cli.save_path_flow import (
    build_content_save_path,
    prompt_for_content_folder_name,
    resolve_save_path,
)
from mikancli.cli.search_flow import resolve_mikan_selection, run_interactive_selection
from mikancli.config import get_config_path, load_config, save_config
from mikancli.core.models import AppConfig, RuleDraft, SearchRequest
from mikancli.core.normalize import collapse_spaces
from mikancli.core.rules import build_rule_draft
from mikancli.display import print_text_summary
from mikancli.i18n import (
    LANGUAGE_LABELS,
    SUPPORTED_LANGUAGES,
    get_language,
    language_from_env,
    normalize_language,
    set_language,
    t,
)

STARTUP_ACTION_SEARCH = "search"
STARTUP_ACTION_QBITTORRENT = "qbittorrent"
STARTUP_ACTION_LANGUAGE = "language"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mikancli",
        description=t("arg.description"),
    )
    parser.add_argument("keyword", nargs="?", help=t("arg.keyword.help"))
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help=t("arg.include.help"),
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help=t("arg.exclude.help"),
    )
    parser.add_argument(
        "--save-path",
        help=t("arg.save_path.help"),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help=t("arg.json.help"),
    )
    parser.add_argument(
        "--setup-qbittorrent",
        action="store_true",
        help=t("arg.setup_qbittorrent.help"),
    )
    parser.add_argument(
        "--language",
        type=parse_language_arg,
        metavar="{en,zh-CN}",
        help=t("arg.language.help"),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def parse_language_arg(value: str) -> str:
    normalized = normalize_language(value)
    if normalized is None:
        supported = ", ".join(SUPPORTED_LANGUAGES)
        raise argparse.ArgumentTypeError(
            t("language.invalid", language=value, supported=supported)
        )
    return normalized


def parse_requested_language(argv: list[str] | None) -> str | None:
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--language")
    args, _ = pre_parser.parse_known_args(argv)
    return args.language


def resolve_startup_language(requested_language: str | None, config: AppConfig) -> str:
    cli_language = normalize_language(requested_language)
    if cli_language:
        return cli_language

    env_language = language_from_env()
    if env_language:
        return env_language

    return normalize_language(config.language) or "en"


def prompt_startup_action() -> str:
    return select_option(
        t("startup.choose_action"),
        [
            (STARTUP_ACTION_SEARCH, t("startup.search")),
            (STARTUP_ACTION_QBITTORRENT, t("startup.qbittorrent")),
            (STARTUP_ACTION_LANGUAGE, t("startup.language")),
        ],
        default=STARTUP_ACTION_SEARCH,
        allow_exit=True,
    )


def run_language_configuration_flow(config: AppConfig, config_path: Path) -> AppConfig:
    selected_language = select_option(
        t("language.choose"),
        [(language, LANGUAGE_LABELS[language]) for language in SUPPORTED_LANGUAGES],
        default=get_language(),
        allow_exit=True,
    )
    set_language(selected_language)
    updated_config = replace(config, language=selected_language)
    save_config(config_path, updated_config)
    print(t("language.saved", language=LANGUAGE_LABELS[selected_language]))
    return updated_config


def build_request_from_args(args: argparse.Namespace, *, config: AppConfig, config_path: Path) -> SearchRequest:

    if not args.keyword:
        raise ValueError(t("request.keyword_required_json"))

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


def build_interactive_draft(args: argparse.Namespace, *, config: AppConfig,config_path: Path) -> RuleDraft:

    bangumi, subgroup = run_interactive_selection(initial_keyword=args.keyword)

    include_words = tuple(args.include) or prompt_word_list(
        t("filters.include_prompt")
    )
    exclude_words = tuple(args.exclude) or prompt_word_list(
        t("filters.exclude_prompt")
    )
    save_path = resolve_save_path(
        args.save_path,
        config,
        prompt_for_default=True,
        config_path=config_path,
    )
    content_folder_name = prompt_for_content_folder_name(bangumi.title, save_path)
    final_save_path = build_content_save_path(save_path, content_folder_name)

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
        notes=(t("draft.review_note"),),
    )


def main(argv: list[str] | None = None) -> int:
    config_path = get_config_path()
    config = load_config(config_path)
    requested_language = parse_requested_language(argv)
    set_language(resolve_startup_language(requested_language, config))

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.language:
        set_language(args.language)

    if args.setup_qbittorrent:
        try:
            return setup_qbittorrent(config, config_path)
        except ExitRequested:
            print(t("common.exited"))
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

    has_startup_menu = args.keyword is None

    while True:
        try:
            if has_startup_menu:
                while True:
                    startup_action = prompt_startup_action()
                    if startup_action == STARTUP_ACTION_QBITTORRENT:
                        setup_exit_code = run_qbittorrent_configuration_flow(config, config_path)
                        if setup_exit_code not in {
                            QBITTORRENT_SETUP_SUCCESS,
                            QBITTORRENT_NOT_CONFIGURED,
                        }:
                            return setup_exit_code
                        config = load_config(config_path)
                        continue
                    if startup_action == STARTUP_ACTION_LANGUAGE:
                        config = run_language_configuration_flow(config, config_path)
                        continue
                    break

            setup_exit_code = prompt_for_qbittorrent_setup_if_needed(
                config,
                config_path,
            )
            if setup_exit_code not in {
                QBITTORRENT_SETUP_SUCCESS,
                QBITTORRENT_NOT_CONFIGURED,
            }:
                return setup_exit_code
            config = load_config(config_path)
            draft = build_interactive_draft(
                args,
                config=config,
                config_path=config_path,
            )
        except ExitRequested:
            print(t("common.exited"))
            return 0

        summary_exit_code = print_text_summary(draft)
        if summary_exit_code != 0:
            return summary_exit_code
        try:
            submission_exit_code = prompt_to_submit_rule_to_qbittorrent(config, draft)
            if submission_exit_code == QBITTORRENT_NOT_CONFIGURED:
                print(t("qb.submit.not_configured"))
                setup_exit_code = prompt_for_qbittorrent_setup_if_needed(config, config_path)
                if setup_exit_code not in {
                    QBITTORRENT_SETUP_SUCCESS,
                    QBITTORRENT_NOT_CONFIGURED, # When user declines but we can still continue to allow them to continue without qBittorrent
                }:
                    return setup_exit_code

                config = load_config(config_path)
                if config.qbittorrent_url:
                    submission_exit_code = prompt_to_submit_rule_to_qbittorrent(config, draft)
                else:
                    continue

        except ExitRequested:
            print(t("common.exited"))
            return 0

        if has_startup_menu and submission_exit_code == QBITTORRENT_SUBMISSION_SKIPPED:
            config = load_config(config_path)
            continue

        return QBITTORRENT_SETUP_SUCCESS if submission_exit_code == QBITTORRENT_SUBMISSION_SKIPPED else submission_exit_code
