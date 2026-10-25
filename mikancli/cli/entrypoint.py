from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

from mikancli import __version__
from mikancli.cli import commands
from mikancli.cli.input_parsing import (
    parse_optional_positive_int,
    prompt_optional_positive_int,
    prompt_word_list,
)
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
from mikancli.display import print_message, print_section, print_text_summary
from mikancli.i18n import (
    LANGUAGE_LABELS,
    SUPPORTED_LANGUAGES,
    get_language,
    language_from_env,
    normalize_language,
    set_language,
    t,
)
from mikancli.integrations.mikan import MikanLookupError
from mikancli.services.errors import CommandError

STARTUP_ACTION_SEARCH = "search"
STARTUP_ACTION_QBITTORRENT = "qbittorrent"
STARTUP_ACTION_LANGUAGE = "language"


def build_parser(*, machine: bool = False) -> argparse.ArgumentParser:
    parser_type = commands.CommandParser if machine else argparse.ArgumentParser
    parser = parser_type(
        prog="mikancli",
        description=t("arg.description"),
        allow_abbrev=False,
        epilog="Noninteractive commands: search, subgroups, feed, rules plan/apply/get, config show, schema. Run mikancli COMMAND --help for details.",
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
        "--min-episode",
        type=parse_min_episode_arg,
        help=t("arg.min_episode.help"),
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
    parser.add_argument("--config", help="Use a specific config file (or set MIKANCLI_CONFIG).")
    parser.add_argument("--timeout", type=commands.positive_timeout, default=15.0,
                        help="Network request timeout in seconds for JSON lookup (default: 15).")
    parser.add_argument("--non-interactive", action="store_true",
                        help="Fail if this invocation would require a prompt.")
    return parser


def parse_language_arg(value: str) -> str:
    normalized = normalize_language(value)
    if normalized is None:
        supported = ", ".join(SUPPORTED_LANGUAGES)
        raise argparse.ArgumentTypeError(
            t("language.invalid", language=value, supported=supported)
        )
    return normalized


def parse_min_episode_arg(value: str) -> int:
    try:
        parsed = parse_optional_positive_int(
            value,
            field_name=t("filters.min_episode_field"),
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if parsed is None:
        raise argparse.ArgumentTypeError(
            t("filters.positive_int_required", field=t("filters.min_episode_field"))
        )
    return parsed


def parse_requested_language(argv: list[str] | None) -> str | None:
    pre_parser = commands.CommandParser(add_help=False, allow_abbrev=False)
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
    print_section("MikanCli")
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
    print_section(t("startup.language"))
    selected_language = select_option(
        t("language.choose"),
        [(language, LANGUAGE_LABELS[language]) for language in SUPPORTED_LANGUAGES],
        default=get_language(),
        allow_exit=True,
    )
    set_language(selected_language)
    updated_config = replace(config, language=selected_language)
    save_config(config_path, updated_config)
    print_message(t("language.saved", language=LANGUAGE_LABELS[selected_language]), style="success")
    return updated_config


def build_request_from_args(args: argparse.Namespace, *, config: AppConfig, config_path: Path) -> SearchRequest:

    if not collapse_spaces(args.keyword or ""):
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
        min_episode=args.min_episode,
        save_path=save_path,
    )


def build_interactive_draft(args: argparse.Namespace, *, config: AppConfig,config_path: Path) -> RuleDraft:

    bangumi, subgroup = run_interactive_selection(initial_keyword=args.keyword)

    if not args.include or not args.exclude or args.min_episode is None:
        print_section(t("ui.filters"))
    include_words = tuple(args.include) or prompt_word_list(
        t("filters.include_prompt")
    )
    exclude_words = tuple(args.exclude) or prompt_word_list(
        t("filters.exclude_prompt")
    )
    min_episode = args.min_episode
    if min_episode is None:
        min_episode = prompt_optional_positive_int(
            t("filters.min_episode_prompt"),
            field_name=t("filters.min_episode_field"),
        )
    print_section(t("ui.save_path"))
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
        min_episode=min_episode,
        rule_name=content_folder_name,
        save_path=final_save_path,
    )
    return build_rule_draft(
        request,
        bangumi=bangumi,
        subgroup=subgroup,
        notes=(t("draft.review_note"),),
    )


def main(argv: list[str] | None = None) -> int:
    actual_argv = list(sys.argv[1:] if argv is None else argv)
    if commands.is_command_invocation(actual_argv):
        return commands.run_commands(actual_argv)
    try:
        return _run(actual_argv)
    except CommandError as exc:
        commands.emit_result(error=exc)
        return exc.exit_code
    except MikanLookupError as exc:
        error = CommandError(getattr(exc, "code", "UPSTREAM_ERROR"), str(exc),
                             retryable=getattr(exc, "retryable", False))
        commands.emit_result(error=error)
        return error.exit_code
    except KeyboardInterrupt:
        print(t("common.cancelled"), file=sys.stderr)
        return 130


def _run(argv: list[str] | None = None) -> int:
    startup_parser = commands.CommandParser(add_help=False, allow_abbrev=False)
    startup_parser.add_argument("--config")
    startup_options, _ = startup_parser.parse_known_args(argv)
    configured_path = startup_options.config or os.environ.get("MIKANCLI_CONFIG")
    config_path = Path(configured_path).expanduser() if configured_path else get_config_path()
    config = load_config(config_path)
    requested_language = parse_requested_language(argv)
    set_language(resolve_startup_language(requested_language, config))

    parser = build_parser(machine="--json" in (argv or []) or "--non-interactive" in (argv or []))
    args = parser.parse_args(argv)

    if args.language:
        set_language(args.language)

    if args.json and args.setup_qbittorrent:
        raise CommandError("INVALID_ARGUMENT", "--setup-qbittorrent requires interactive input and cannot be combined with --json.", exit_code=2)
    if not args.json and (args.non_interactive or not sys.stdin.isatty()):
        raise CommandError("INTERACTIVE_REQUIRED", "This invocation requires a terminal. Use search, subgroups, feed, or rules plan/apply/get for noninteractive usage.", exit_code=2)

    if args.setup_qbittorrent:
        try:
            return setup_qbittorrent(config, config_path)
        except ExitRequested:
            print_message(t("common.exited"))
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

        bangumi, subgroup, lookup_notes = resolve_mikan_selection(request, timeout=args.timeout)
        draft = build_rule_draft(
            request,
            bangumi=bangumi,
            subgroup=subgroup,
            notes=lookup_notes,
        )
        print(json.dumps(draft.to_dict(), ensure_ascii=True, indent=2))
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
            print_message(t("common.exited"))
            return 0

        summary_exit_code = print_text_summary(draft)
        if summary_exit_code != 0:
            return summary_exit_code
        try:
            submission_exit_code = prompt_to_submit_rule_to_qbittorrent(config, draft)
            if submission_exit_code == QBITTORRENT_NOT_CONFIGURED:
                print_message(t("qb.submit.not_configured"), style="warning")
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
            print_message(t("common.exited"))
            return 0

        if has_startup_menu and submission_exit_code == QBITTORRENT_SUBMISSION_SKIPPED:
            config = load_config(config_path)
            continue

        return QBITTORRENT_SETUP_SUCCESS if submission_exit_code == QBITTORRENT_SUBMISSION_SKIPPED else submission_exit_code
