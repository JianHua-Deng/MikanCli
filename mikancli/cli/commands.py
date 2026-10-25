"""Noninteractive command interface. JSON stdout is a versioned public contract."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import asdict, replace
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from mikancli.config import get_config_path, load_config
from mikancli.core.models import AppConfig, QBittorrentSettings
from mikancli.integrations.mikan import (
    MikanLookupError,
    fetch_mikan_feed_items,
    fetch_mikan_subgroups,
    search_mikan_bangumi,
)
from mikancli.integrations.qbittorrent_client import QBittorrentError
from mikancli.services.errors import CommandError
from mikancli.services.rules import (
    apply_plan,
    build_plan,
    get_rule,
    plan_schema,
    validate_plan,
)

COMMANDS = {"search", "subgroups", "feed", "rules", "config", "schema"}
SCHEMA_VERSION = 1


class CommandParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CommandError("INVALID_ARGUMENT", message, exit_code=2)


def is_command_invocation(argv: list[str]) -> bool:
    """Recognize reserved commands without mistaking option values for commands."""
    value_options = {
        "--config", "--timeout", "--language", "--include", "--exclude",
        "--min-episode", "--save-path",
    }
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--":
            return False
        if token in value_options:
            index += 2
            continue
        if token.startswith("--") and "=" in token:
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token in COMMANDS
    return False


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def nonnegative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a nonnegative integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    return parsed


def positive_timeout(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("timeout must be a positive number of seconds") from exc
    if not math.isfinite(parsed) or not 0 < parsed <= 300:
        raise argparse.ArgumentTypeError("timeout must be greater than 0 and at most 300 seconds")
    return parsed


def nonempty_text(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("must not be empty")
    return value.strip()


def add_common_options(parser: argparse.ArgumentParser) -> None:
    # SUPPRESS preserves values supplied before a subcommand when parsing its child.
    parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="Return JSON (the default for these commands).")
    parser.add_argument("--non-interactive", action="store_true", default=argparse.SUPPRESS,
                        help="Never prompt (these commands always run without prompts).")
    parser.add_argument("--config", type=nonempty_text, default=argparse.SUPPRESS,
                        help="Config file; overrides MIKANCLI_CONFIG and the user config path.")
    parser.add_argument("--timeout", type=positive_timeout, default=argparse.SUPPRESS,
                        help="Per-request timeout in seconds (default: 15).")
    parser.add_argument("--language", choices=("en", "zh-CN"), default=argparse.SUPPRESS,
                        help="Accepted for compatibility; JSON keys and error codes are stable.")


def build_command_parser() -> argparse.ArgumentParser:
    parser = CommandParser(prog="mikancli", allow_abbrev=False,
                           description="Noninteractive Mikan discovery and qBittorrent rule commands.")
    add_common_options(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def command(parent, name, help_text):
        child = parent.add_parser(name, help=help_text, allow_abbrev=False)
        add_common_options(child)
        return child

    search = command(subparsers, "search", "List matching anime; never select automatically.")
    search.add_argument("keyword", type=nonempty_text)
    search.add_argument("--limit", type=positive_int, default=20)
    search.add_argument("--offset", type=nonnegative_int, default=0)
    subgroups = command(subparsers, "subgroups", "List feeds for an anime ID.")
    subgroups.add_argument("--bangumi-id", type=positive_int, required=True)
    feed = command(subparsers, "feed", "Preview an explicitly selected feed.")
    feed.add_argument("--bangumi-id", type=positive_int, required=True)
    feed.add_argument("--subgroup-id", type=positive_int, required=True)
    feed.add_argument("--limit", type=positive_int, default=20)
    feed.add_argument("--offset", type=nonnegative_int, default=0)
    rules = command(subparsers, "rules", "Plan, apply, or inspect RSS rules.")
    actions = rules.add_subparsers(dest="action", required=True)
    plan = command(actions, "plan", "Build an exact rule plan without changing qBittorrent.")
    plan.add_argument("--bangumi-id", type=positive_int, required=True)
    plan.add_argument("--subgroup-id", type=positive_int, required=True)
    plan.add_argument("--name", type=nonempty_text, required=True)
    plan.add_argument("--include", action="append", default=[])
    plan.add_argument("--exclude", action="append", default=[])
    plan.add_argument("--min-episode", type=positive_int)
    plan.add_argument("--save-path",
                      help="Exact destination; no extra title folder is appended.")
    plan.add_argument("--category")
    plan.add_argument("--add-paused", action=argparse.BooleanOptionalAction, default=None)
    plan.add_argument("--feed-path", type=nonempty_text)
    apply = command(actions, "apply", "Apply a reviewed plan; may start matching downloads.")
    apply.add_argument("--file", type=nonempty_text, required=True, help="Plan file, or - for stdin.")
    apply.add_argument("--if-exists", choices=("fail", "replace"), default="fail")
    get = command(actions, "get", "Read a saved rule and its feed state.")
    get.add_argument("--name", type=nonempty_text, required=True)
    config = command(subparsers, "config", "Inspect effective configuration with secrets redacted.")
    config_actions = config.add_subparsers(dest="action", required=True)
    command(config_actions, "show", "Show configuration and credential presence.")
    command(subparsers, "schema", "Print the result envelope and rule plan JSON Schemas.")
    return parser


def load_command_config(args: argparse.Namespace) -> tuple[Path, AppConfig]:
    configured_path = getattr(args, "config", None) or os.environ.get("MIKANCLI_CONFIG")
    path = Path(configured_path).expanduser() if configured_path else get_config_path()
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise CommandError("INVALID_CONFIG", "Cannot read a valid JSON config object.", exit_code=2) from exc
        if not isinstance(payload, dict):
            raise CommandError("INVALID_CONFIG", "Config must be a JSON object.", exit_code=2)
    config = load_config(path)
    overrides = {}
    for field, env_name in (
        ("qbittorrent_url", "MIKANCLI_QBITTORRENT_URL"),
        ("qbittorrent_username", "MIKANCLI_QBITTORRENT_USERNAME"),
        ("qbittorrent_password", "MIKANCLI_QBITTORRENT_PASSWORD"),
    ):
        if env_name in os.environ:
            overrides[field] = os.environ[env_name] or None
    return path, replace(config, **overrides)


def settings_for(config: AppConfig) -> QBittorrentSettings:
    if not config.qbittorrent_url:
        raise CommandError("NOT_CONFIGURED", "Set MIKANCLI_QBITTORRENT_URL or configure qBittorrent.", exit_code=3)
    url = config.qbittorrent_url
    try:
        parts = urlsplit(url if "://" in url else "http://" + url)
        parts.port
    except ValueError as exc:
        raise CommandError("INVALID_CONFIG", "qBittorrent URL has an invalid hostname or port.", exit_code=2) from exc
    if (parts.scheme not in {"http", "https"} or not parts.hostname
            or parts.username is not None or parts.password is not None or parts.query or parts.fragment):
        raise CommandError("INVALID_CONFIG", "qBittorrent URL must be HTTP(S) without embedded credentials, query, or fragment.", exit_code=2)
    return QBittorrentSettings(url, config.qbittorrent_username, config.qbittorrent_password)


def read_plan(source: str) -> dict[str, object]:
    try:
        content = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8-sig")
        payload = json.loads(content.lstrip("\ufeff"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise CommandError("INVALID_ARGUMENT", "Cannot read plan JSON from the specified file or stdin.", exit_code=2) from exc
    if isinstance(payload, dict) and "schema_version" in payload:
        if type(payload.get("schema_version")) is not int or payload["schema_version"] != SCHEMA_VERSION or payload.get("ok") is not True or payload.get("error") is not None:
            raise CommandError("INVALID_ARGUMENT", "Expected a successful version 1 plan result.", exit_code=2)
        payload = payload.get("data")
    return validate_plan(payload)


def envelope_schema() -> dict[str, object]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "MikanCli command result v1",
        "type": "object",
        "required": ["schema_version", "ok", "data", "error"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "ok": {"type": "boolean"},
            "data": {"type": ["object", "null"]},
            "error": {"type": ["object", "null"], "properties": {
                "code": {"type": "string"}, "message": {"type": "string"},
                "retryable": {"type": "boolean"}, "details": {"type": "object"},
            }, "required": ["code", "message", "retryable", "details"], "additionalProperties": False},
        },
        "oneOf": [
            {"properties": {"ok": {"const": True}, "data": {"type": "object"}, "error": {"type": "null"}}},
            {"properties": {"ok": {"const": False}, "data": {"type": "null"}, "error": {"type": "object"}}},
        ],
    }


def dispatch(args: argparse.Namespace) -> dict[str, object]:
    if args.command == "schema":
        return {"envelope": envelope_schema(), "plan": plan_schema()}
    path, config = load_command_config(args)
    timeout = getattr(args, "timeout", 15.0)
    if args.command == "search":
        results = search_mikan_bangumi(args.keyword, timeout=timeout)
        return {"items": [asdict(item) for item in results[args.offset:args.offset + args.limit]],
                "total": len(results), "offset": args.offset, "limit": args.limit}
    if args.command == "subgroups":
        return {"bangumi_id": args.bangumi_id,
                "items": [asdict(item) for item in fetch_mikan_subgroups(args.bangumi_id, timeout=timeout)]}
    if args.command == "feed":
        groups = fetch_mikan_subgroups(args.bangumi_id, timeout=timeout)
        group = next((item for item in groups if item.subgroup_id == args.subgroup_id), None)
        if group is None:
            raise CommandError("NOT_FOUND", "Subgroup does not belong to the selected anime.", exit_code=3)
        items = fetch_mikan_feed_items(group.feed_url, timeout=timeout)
        return {"bangumi_id": args.bangumi_id, "subgroup": asdict(group),
                "items": [asdict(item) for item in items[args.offset:args.offset + args.limit]],
                "total": len(items), "offset": args.offset, "limit": args.limit}
    if args.command == "config":
        data = asdict(config)
        data["qbittorrent_username"] = "[REDACTED]" if config.qbittorrent_username else None
        data["qbittorrent_password"] = "[REDACTED]" if config.qbittorrent_password else None
        if config.qbittorrent_url:
            parts = urlsplit(config.qbittorrent_url if "://" in config.qbittorrent_url else "http://" + config.qbittorrent_url)
            # Never echo userinfo, query tokens, or fragments from a configured URL.
            data["qbittorrent_url"] = urlunsplit((parts.scheme, parts.netloc.rsplit("@", 1)[-1], parts.path, "", ""))
        return {"config_path": str(path.resolve()), "settings": data}
    if args.action == "plan":
        return build_plan(
            bangumi_id=args.bangumi_id, subgroup_id=args.subgroup_id, name=args.name,
            include=tuple(args.include), exclude=tuple(args.exclude), min_episode=args.min_episode,
            save_path=args.save_path if args.save_path is not None else config.default_save_path,
            category=args.category if args.category is not None else config.qbittorrent_category,
            add_paused=args.add_paused if args.add_paused is not None else config.qbittorrent_add_paused,
            feed_path=args.feed_path, timeout=timeout,
        )
    if args.action == "apply":
        plan = read_plan(args.file)  # Validate before connecting to qBittorrent.
        return apply_plan(settings_for(config), plan, if_exists=args.if_exists, timeout=timeout)
    return get_rule(settings_for(config), args.name, timeout=timeout)


def emit_result(data: dict[str, object] | None = None, error: CommandError | None = None) -> None:
    print(json.dumps({"schema_version": SCHEMA_VERSION, "ok": error is None,
                      "data": data if error is None else None,
                      "error": error.to_dict() if error else None}, ensure_ascii=True, indent=2, allow_nan=False))


def run_commands(argv: list[str]) -> int:
    try:
        args = build_command_parser().parse_args(argv)
        data = dispatch(args)
    except CommandError as exc:
        emit_result(error=exc)
        return exc.exit_code
    except (MikanLookupError, QBittorrentError) as exc:
        code = getattr(exc, "code", "UPSTREAM_ERROR")
        error = CommandError(code, str(exc), retryable=getattr(exc, "retryable", False))
        emit_result(error=error)
        return error.exit_code
    except KeyboardInterrupt:
        emit_result(error=CommandError("CANCELLED", "Command cancelled.", exit_code=130))
        return 130
    except (OSError, ValueError) as exc:
        emit_result(error=CommandError("INVALID_ARGUMENT", "Cannot read the requested configuration or input.", exit_code=2))
        return 2
    emit_result(data=data)
    return 0
