"""Reviewable, noninteractive RSS rule operations for command-line agents."""

from __future__ import annotations

from copy import deepcopy
import ntpath
from urllib.parse import urlsplit

from mikancli.core.models import QBittorrentSettings, SearchRequest
from mikancli.core.normalize import collapse_spaces
from mikancli.core.rules import build_rule_draft
from mikancli.integrations.mikan import MikanLookupError, fetch_mikan_subgroups
from mikancli.integrations.qbittorrent import (
    build_default_feed_path,
    build_qbittorrent_rule_definition,
)
from mikancli.integrations.qbittorrent_client import QBittorrentClient, QBittorrentError
from mikancli.services.errors import CommandError

PLAN_VERSION = 1
_MAX_TEXT = 256
_MAX_PATH = 4096
_MAX_URL = 8192
_MAX_REGEX = 65536
_BOOLEAN_FIELDS = {"enabled", "useRegex", "smartFilter", "addPaused"}
_TEXT_FIELDS = {
    "mustContain": _MAX_REGEX,
    "mustNotContain": _MAX_REGEX,
    "episodeFilter": _MAX_PATH,
    "assignedCategory": _MAX_TEXT,
    "savePath": _MAX_PATH,
}
_RULE_FIELDS = _BOOLEAN_FIELDS | _TEXT_FIELDS.keys() | {"affectedFeeds", "ignoreDays"}
_PLAN_FIELDS = {"plan_version", "rule_name", "feed_url", "feed_path", "rule_definition"}


def _invalid(message: str) -> CommandError:
    return CommandError("INVALID_ARGUMENT", message, exit_code=2)


def _text(value: object, label: str, maximum: int, *, nonempty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum:
        raise _invalid(f"{label} must be a string of at most {maximum} characters.")
    if any(ord(character) < 32 for character in value):
        raise _invalid(f"{label} cannot contain control characters.")
    if nonempty and not value.strip():
        raise _invalid(f"{label} must not be empty.")
    return value


def _positive_id(value: object, label: str) -> int:
    if type(value) is not int or not 1 <= value <= 2147483647:
        raise _invalid(f"{label} must be an integer between 1 and 2147483647.")
    return value


def _timeout(value: object) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0 < value <= 300
    ):
        raise _invalid("timeout must be a number greater than 0 and at most 300 seconds.")
    return float(value)


def _feed_url(value: object, label: str = "feed_url") -> str:
    url = _text(value, label, _MAX_URL, nonempty=True)
    try:
        parts = urlsplit(url)
        # Accessing port also detects malformed port numbers.
        parts.port
    except ValueError as exc:
        raise _invalid(f"{label} must be a valid HTTP or HTTPS URL.") from exc
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.fragment
        or any(character.isspace() for character in url)
    ):
        raise _invalid(f"{label} must be an HTTP or HTTPS URL without credentials or a fragment.")
    return url


def _integration_error(exc: Exception) -> CommandError:
    return CommandError(
        getattr(exc, "code", "UPSTREAM_ERROR"),
        str(exc),
        retryable=getattr(exc, "retryable", False),
    )


def build_plan(
    *,
    bangumi_id: int,
    subgroup_id: int,
    name: str,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
    min_episode: int | None = None,
    save_path: str | None = None,
    category: str | None = None,
    add_paused: bool = False,
    feed_path: str | None = None,
    timeout: float = 15,
) -> dict:
    """Resolve the explicit subgroup and return the exact configurable rule payload."""
    _positive_id(bangumi_id, "bangumi_id")
    _positive_id(subgroup_id, "subgroup_id")
    rule_name = collapse_spaces(_text(name, "name", _MAX_TEXT, nonempty=True))
    for label, terms in (("include", include), ("exclude", exclude)):
        if not isinstance(terms, (tuple, list)) or len(terms) > 64:
            raise _invalid(f"{label} must contain at most 64 string terms.")
        for term in terms:
            _text(term, f"{label} term", _MAX_TEXT, nonempty=True)
    if min_episode is not None:
        _positive_id(min_episode, "min_episode")
    if save_path is not None:
        _text(save_path, "save_path", _MAX_PATH)
    if category is not None:
        _text(category, "category", _MAX_TEXT)
    if type(add_paused) is not bool:
        raise _invalid("add_paused must be a boolean.")
    if feed_path is not None:
        _text(feed_path, "feed_path", _MAX_PATH, nonempty=True)
    request_timeout = _timeout(timeout)
    try:
        subgroups = fetch_mikan_subgroups(bangumi_id, timeout=request_timeout)
    except MikanLookupError as exc:
        raise _integration_error(exc) from exc
    subgroup = next((item for item in subgroups if item.subgroup_id == subgroup_id), None)
    if subgroup is None:
        raise CommandError(
            "NOT_FOUND",
            f"Subgroup {subgroup_id} is not available for Bangumi {bangumi_id}.",
            exit_code=3,
            details={"bangumi_id": bangumi_id, "subgroup_id": subgroup_id},
        )
    draft = build_rule_draft(
        SearchRequest(
            keyword=rule_name,
            rule_name=rule_name,
            include_words=tuple(include),
            exclude_words=tuple(exclude),
            min_episode=min_episode,
            save_path=save_path,
        ),
        subgroup=subgroup,
    )
    definition = build_qbittorrent_rule_definition(
        draft, add_paused=add_paused, assigned_category=category
    )
    # Runtime history stays out of the plan. Replacement merges it from the server.
    definition.pop("previouslyMatchedEpisodes", None)
    definition.pop("lastMatch", None)
    return validate_plan(
        {
            "plan_version": PLAN_VERSION,
            "rule_name": rule_name,
            "feed_url": subgroup.feed_url,
            "feed_path": collapse_spaces(feed_path) if feed_path else build_default_feed_path(draft),
            "rule_definition": definition,
        }
    )


def validate_plan(payload: object) -> dict:
    """Reject malformed or ambiguous plans before any qBittorrent requests."""
    if not isinstance(payload, dict) or payload.keys() != _PLAN_FIELDS:
        raise _invalid("A plan must contain exactly plan_version, rule_name, feed_url, feed_path, and rule_definition.")
    if type(payload["plan_version"]) is not int or payload["plan_version"] != PLAN_VERSION:
        raise _invalid(f"plan_version must be {PLAN_VERSION}.")
    name = _text(payload["rule_name"], "rule_name", _MAX_TEXT, nonempty=True)
    path = _text(payload["feed_path"], "feed_path", _MAX_PATH, nonempty=True)
    if name != collapse_spaces(name) or path != collapse_spaces(path):
        raise _invalid("rule_name and feed_path must have normalized whitespace.")
    url = _feed_url(payload["feed_url"])
    definition = payload["rule_definition"]
    if not isinstance(definition, dict) or definition.keys() != _RULE_FIELDS:
        raise _invalid("rule_definition must contain exactly the configurable fields in the plan schema; runtime history fields are not allowed.")
    for field in _BOOLEAN_FIELDS:
        if type(definition[field]) is not bool:
            raise _invalid(f"rule_definition.{field} must be a boolean.")
    for field, maximum in _TEXT_FIELDS.items():
        _text(definition[field], f"rule_definition.{field}", maximum)
    category = definition["assignedCategory"]
    if category != collapse_spaces(category):
        raise _invalid("rule_definition.assignedCategory must have normalized whitespace.")
    days = definition["ignoreDays"]
    if type(days) is not int or not 0 <= days <= 2147483647:
        raise _invalid("rule_definition.ignoreDays must be an integer between 0 and 2147483647.")
    if not isinstance(definition["affectedFeeds"], list) or definition["affectedFeeds"] != [url]:
        raise _invalid("rule_definition.affectedFeeds must contain exactly the plan's feed_url.")
    return {
        "plan_version": PLAN_VERSION,
        "rule_name": name,
        "feed_url": url,
        "feed_path": path,
        "rule_definition": {**definition, "affectedFeeds": [url]},
    }


def _contains_feed(tree: dict, feed_url: str) -> bool:
    """Read folder trees with scalar URL leaves or current {uid, url} leaves."""
    pending = [tree]
    while pending:
        value = pending.pop()
        if isinstance(value.get("url"), str):
            if value["url"] == feed_url:
                return True
            # This is a feed object. Its titles/articles are metadata, not feeds.
            continue
        for child in value.values():
            if isinstance(child, str) and child == feed_url:
                return True
            if isinstance(child, dict):
                pending.append(child)
    return False


def _effective_rule(actual: dict) -> dict:
    """Match qBittorrent's nested torrentParams precedence over legacy fields."""
    effective = dict(actual)
    if "torrentParams" in actual:
        parameters = actual["torrentParams"]
        parameters = parameters if isinstance(parameters, dict) else {}
        for field, parameter in (
            ("savePath", "save_path"), ("assignedCategory", "category"),
        ):
            value = parameters.get(parameter)
            effective[field] = value if isinstance(value, str) else ""
        value = parameters.get("stopped")
        effective["addPaused"] = value if type(value) is bool else None
    return effective


def _mismatched_fields(actual: object, expected: dict) -> list[str]:
    if not isinstance(actual, dict):
        return sorted(expected)
    effective = _effective_rule(actual)
    mismatches = {
        key for key, value in expected.items()
        if key not in effective or type(effective[key]) is not type(value)
        or not (_same_save_path(effective[key], value) if key == "savePath" else effective[key] == value)
    }
    parameters = actual.get("torrentParams")
    if expected.get("savePath") and isinstance(parameters, dict) and parameters.get("use_auto_tmm") is True:
        # Auto TMM can override this stored path with the category's destination.
        mismatches.add("savePath")
    return sorted(mismatches)


def _same_save_path(actual: str, expected: str) -> bool:
    """Compare server paths lexically without interpreting them on this computer."""
    if not actual or not expected:
        return actual == expected
    windows_style = any(ntpath.splitdrive(path)[0] for path in (actual, expected))
    if windows_style:
        def normalized(path: str) -> str:
            value = ntpath.normpath(path)
            drive, tail = ntpath.splitdrive(value)
            # Both spellings of a UNC share root represent the same location.
            if drive.startswith("\\\\") and tail in {"", "\\"}:
                return drive + "\\"
            return value
        return normalized(actual) == normalized(expected)
    # A backslash can be part of a POSIX filename; only '/' is a separator here.
    return (actual.rstrip("/") or "/") == (expected.rstrip("/") or "/")


def _replacement_definition(actual: dict, planned: dict) -> dict:
    # setRule replaces the whole rule. Omitted history and advanced settings reset.
    definition = deepcopy(actual)
    definition.update(deepcopy(planned))
    parameters = definition.get("torrentParams")
    if isinstance(parameters, dict):
        parameters.update({
            "stopped": planned["addPaused"],
            "category": planned["assignedCategory"],
            "save_path": planned["savePath"],
        })
        if planned["savePath"]:
            # Legacy parsing disables Auto TMM for an explicit save path too.
            parameters["use_auto_tmm"] = False
    return definition


def _partial(
    plan: dict,
    stages: dict,
    *,
    cause: BaseException | None = None,
    verification: dict | None = None,
) -> CommandError:
    details: dict[str, object] = {
        "rule_name": plan["rule_name"],
        "feed_url": plan["feed_url"],
        "stages": dict(stages),
        "next_action": "Inspect this rule with rules get before retrying the saved plan.",
    }
    if cause is not None:
        details["cause"] = (
            {"code": "INTERRUPTED", "message": "The operation was interrupted."}
            if isinstance(cause, KeyboardInterrupt)
            else {"code": getattr(cause, "code", "UPSTREAM_ERROR"), "message": str(cause)}
        )
    if verification is not None:
        details["verification"] = verification
    return CommandError(
        "PARTIAL_SUCCESS",
        "A qBittorrent write was attempted, but the complete saved state could not be verified.",
        exit_code=5,
        details=details,
    )


def apply_plan(
    settings: QBittorrentSettings,
    plan: dict,
    *,
    if_exists: str = "fail",
    timeout: float = 15,
) -> dict:
    """Apply once, handle conflicts explicitly, and verify every planned setting."""
    reviewed = validate_plan(plan)
    if not isinstance(if_exists, str) or if_exists not in {"fail", "replace"}:
        raise _invalid("if_exists must be 'fail' or 'replace'.")
    request_timeout = _timeout(timeout)
    name = reviewed["rule_name"]
    url = reviewed["feed_url"]
    definition = reviewed["rule_definition"]
    stages = {
        "rule_checked": False,
        "feed_checked": False,
        "feed_add_attempted": False,
        "feed_added": False,
        "rule_write_attempted": False,
        "rule_saved": False,
        "verification_completed": False,
    }
    try:
        client = QBittorrentClient(settings, timeout=request_timeout)
        client.login()
        existing = client.get_auto_downloading_rules()
        stages["rule_checked"] = True
        exists = name in existing
        if exists and not isinstance(existing[name], dict):
            raise CommandError("UPSTREAM_ERROR", "qBittorrent returned an invalid rule definition.")
        differences = _mismatched_fields(existing.get(name), definition)
        if exists and differences and if_exists == "fail":
            raise CommandError(
                "CONFLICT",
                f"Rule {name!r} already exists with different settings. Use --if-exists replace to update it.",
                exit_code=4,
                details={"rule_name": name, "mismatched_fields": differences},
            )
        feed_exists = _contains_feed(client.get_rss_items(), url)
        stages["feed_checked"] = True
        if not feed_exists:
            stages["feed_add_attempted"] = True
            client.add_feed(url, path=reviewed["feed_path"])
            stages["feed_added"] = True
        if not exists or differences:
            write_definition = (
                _replacement_definition(existing[name], definition) if exists
                else deepcopy(definition)
            )
            stages["rule_write_attempted"] = True
            client.set_auto_downloading_rule(name, write_definition)
            stages["rule_saved"] = True
        actual_rules = client.get_auto_downloading_rules()
        actual_tree = client.get_rss_items()
        mismatches = _mismatched_fields(actual_rules.get(name), definition)
        verification = {
            "feed_verified": _contains_feed(actual_tree, url),
            "rule_verified": not mismatches,
            "mismatched_fields": mismatches,
        }
        stages["verification_completed"] = True
        if not verification["feed_verified"] or not verification["rule_verified"]:
            if stages["feed_add_attempted"] or stages["rule_write_attempted"]:
                raise _partial(reviewed, stages, verification=verification)
            raise CommandError(
                "VERIFICATION_FAILED", "qBittorrent state changed while checking the existing rule.",
                details={"rule_name": name, "verification": verification, "stages": stages},
            )
    except KeyboardInterrupt as exc:
        if stages["feed_add_attempted"] or stages["rule_write_attempted"]:
            raise _partial(reviewed, stages, cause=exc) from exc
        raise
    except QBittorrentError as exc:
        if stages["feed_add_attempted"] or stages["rule_write_attempted"]:
            raise _partial(reviewed, stages, cause=exc) from exc
        raise _integration_error(exc) from exc
    return {
        "status": "created" if not exists else ("updated" if differences else "unchanged"),
        "rule_name": name,
        "feed_url": url,
        "feed_added": stages["feed_added"],
        "rule_written": stages["rule_saved"],
        "verification": verification,
        "stages": stages,
    }


def get_rule(settings: QBittorrentSettings, name: str, *, timeout: float = 15) -> dict:
    """Read a named rule and report whether each of its feeds is installed."""
    rule_name = collapse_spaces(_text(name, "name", _MAX_TEXT, nonempty=True))
    request_timeout = _timeout(timeout)
    try:
        client = QBittorrentClient(settings, timeout=request_timeout)
        client.login()
        rules = client.get_auto_downloading_rules()
        if rule_name not in rules:
            raise CommandError("NOT_FOUND", f"Rule {rule_name!r} does not exist.", exit_code=3)
        definition = rules[rule_name]
        if not isinstance(definition, dict):
            raise CommandError("UPSTREAM_ERROR", "qBittorrent returned an invalid rule definition.")
        affected = definition.get("affectedFeeds")
        if not isinstance(affected, list) or any(not isinstance(url, str) for url in affected):
            raise CommandError("UPSTREAM_ERROR", "qBittorrent returned invalid affectedFeeds for the rule.")
        tree = client.get_rss_items()
    except QBittorrentError as exc:
        raise _integration_error(exc) from exc
    feeds = [{"feed_url": url, "exists": _contains_feed(tree, url)} for url in affected]
    return {
        "rule_name": rule_name,
        "rule_definition": definition,
        "feed_exists": bool(feeds) and all(feed["exists"] for feed in feeds),
        "feeds": feeds,
    }


def plan_schema() -> dict:
    """Return the versioned saved-plan schema without requiring a live service."""
    text = lambda maximum: {"type": "string", "maxLength": maximum, "pattern": r"^[^\u0000-\u001f]*$"}
    rule_properties = {field: {"type": "boolean"} for field in sorted(_BOOLEAN_FIELDS)}
    rule_properties.update({field: text(maximum) for field, maximum in _TEXT_FIELDS.items()})
    url_schema = {
        "type": "string", "minLength": 1, "maxLength": _MAX_URL,
        "format": "uri", "pattern": r"^[hH][tT][tT][pP][sS]?://[^/?#@\s]+(?:[/?][^\s#]*)?$",
    }
    rule_properties.update({
        "ignoreDays": {"type": "integer", "minimum": 0, "maximum": 2147483647},
        "affectedFeeds": {"type": "array", "minItems": 1, "maxItems": 1, "items": url_schema},
    })
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "MikanCli rule plan version 1",
        "description": "affectedFeeds must equal [feed_url]. Names, feed paths, and categories use normalized whitespace. Runtime history is excluded.",
        "type": "object",
        "additionalProperties": False,
        "required": sorted(_PLAN_FIELDS),
        "properties": {
            "plan_version": {"type": "integer", "const": PLAN_VERSION},
            "rule_name": {**text(_MAX_TEXT), "minLength": 1},
            "feed_url": url_schema,
            "feed_path": {**text(_MAX_PATH), "minLength": 1},
            "rule_definition": {
                "type": "object", "additionalProperties": False,
                "required": sorted(_RULE_FIELDS), "properties": rule_properties,
            },
        },
    }
