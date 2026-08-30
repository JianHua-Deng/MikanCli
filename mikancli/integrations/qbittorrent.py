from __future__ import annotations

import re

from mikancli.core.models import QBittorrentSettings, RuleDraft
from mikancli.core.normalize import collapse_spaces, sanitize_folder_name
from mikancli.integrations.qbittorrent_client import (
    QBittorrentClient,
    QBittorrentError,
    QBittorrentSubmissionResult,
    nested_value_contains,
    normalize_qbittorrent_url,
    rules_contain_rule_for_feed,
)


def build_qbittorrent_rule_definition(draft: RuleDraft, *, add_paused: bool = False, assigned_category: str | None = None) -> dict[str, object]:
    """
    Convert a RuleDraft into the JSON shape qBittorrent expects for an RSS auto-download rule.
    Returns a dictionary ready to encode as the WebUI ruleDef payload.
    Example: a draft with feed_url="https://example.test/rss" and must_contain=("HEVC",) returns affectedFeeds=["https://example.test/rss"] and mustContain="(?=.*HEVC).*".
    """
    if not draft.feed_url:
        raise QBittorrentError(
            "RSS feed URL is required before building a qBittorrent rule."
        )

    must_contain = build_required_terms_regex(
        draft.must_contain,
        min_episode=draft.min_episode,
    )
    must_not_contain = build_rejected_terms_regex(draft.must_not_contain)

    return {
        "enabled": True,
        "mustContain": must_contain,
        "mustNotContain": must_not_contain,
        "useRegex": bool(must_contain or must_not_contain),
        "episodeFilter": "",
        "smartFilter": False,
        "previouslyMatchedEpisodes": [],
        "affectedFeeds": [draft.feed_url],
        "ignoreDays": 0,
        "lastMatch": "",
        "addPaused": add_paused,
        "assignedCategory": collapse_spaces(assigned_category or ""),
        "savePath": draft.save_path or "",
    }


def build_required_terms_regex(
    terms: tuple[str, ...],
    *,
    min_episode: int | None = None,
) -> str:
    """
    Builds a positive-lookahead regex that requires every cleaned term to appear somewhere in a release title.
    qBittorrent uses the result as the rule's "must contain" filter, so all include words must match.
    Example: before ("HEVC", "1080p") -> result "(?=.*HEVC)(?=.*1080p).*".
    """
    cleaned_terms = clean_rule_terms(terms)
    episode_regex = (
        build_min_episode_title_regex(min_episode)
        if min_episode is not None
        else ""
    )
    if not cleaned_terms and not episode_regex:
        return ""
    literal_lookaheads = "".join(
        f"(?=.*{re.escape(term)})" for term in cleaned_terms
    )
    episode_lookahead = f"(?=.*{episode_regex})" if episode_regex else ""
    return literal_lookaheads + episode_lookahead + ".*"


def build_min_episode_title_regex(min_episode: int | None) -> str:
    """
    Build the raw regex used to match common anime RSS title episode numbers.
    Example: min_episode=1126 matches "[SubsPlease] One Piece - 1126 (1080p)" and "[Group][One Piece][1126][1080p]".
    """
    if min_episode is None:
        return ""
    if min_episode < 1:
        raise ValueError("Minimum episode must be a positive integer.")
    number_regex = build_minimum_number_regex(min_episode)
    return rf"(?:-\s*0*(?:{number_regex})(?=\D|$)|\[\s*0*(?:{number_regex})\s*\])"


def build_minimum_number_regex(minimum: int) -> str:
    """
    Build a regex alternation for positive integers greater than or equal to minimum.
    Example: minimum=1126 returns an alternation that matches 1126, 1127, 1130, 1200, and 10000.
    """
    if minimum < 1:
        raise ValueError("Minimum must be a positive integer.")

    minimum_text = str(minimum)
    width = len(minimum_text)
    alternatives = [minimum_text]

    for index in range(width - 1, -1, -1):
        digit_text = minimum_text[index]
        digit = int(digit_text)
        if digit == 9:
            continue

        next_digit = digit + 1
        prefix = minimum_text[:index]
        remaining = width - index - 1
        higher_digit = (
            str(next_digit) if next_digit == 9 else f"[{next_digit}-9]"
        )
        alternatives.append(prefix + higher_digit + digit_wildcard(remaining))

    alternatives.append(rf"[1-9]\d{{{width},}}")
    return "|".join(alternatives)


def digit_wildcard(count: int) -> str:
    if count <= 0:
        return ""
    if count == 1:
        return r"\d"
    return rf"\d{{{count}}}"


def build_rejected_terms_regex(terms: tuple[str, ...]) -> str:
    """
    Builds an alternation regex that rejects a release title when any cleaned term appears.
    qBittorrent uses the result as the rule's "must not contain" filter, so one matching exclude word is enough.
    Example: before ("720p", "CHT") -> result "720p|CHT".
    """
    cleaned_terms = clean_rule_terms(terms)
    if not cleaned_terms:
        return ""
    return "|".join(re.escape(term) for term in cleaned_terms)


def clean_rule_terms(terms: tuple[str, ...]) -> tuple[str, ...]:
    """Trim rule filter terms and drop empty values before building qBittorrent regex strings. Example: clean_rule_terms((" HEVC ", "")) returns ("HEVC",)."""
    cleaned_terms: list[str] = []
    for term in terms:
        cleaned = collapse_spaces(term)
        if cleaned:
            cleaned_terms.append(cleaned)
    return tuple(cleaned_terms)


def build_default_feed_path(draft: RuleDraft) -> str:
    """Create a safe default qBittorrent RSS feed folder name from the rule name. Example: build_default_feed_path(draft) returns "Re Zero" for a rule named "Re: Zero?"."""
    cleaned_rule_name = sanitize_folder_name(draft.rule_name)
    return cleaned_rule_name or "MikanCli Feed"


def qbittorrent_rule_exists(settings: QBittorrentSettings, rule_name: str) -> bool:
    """Return whether qBittorrent already has an RSS auto-download rule with the given name."""
    client = QBittorrentClient(settings)
    client.login()
    rules = client.get_auto_downloading_rules()
    return collapse_spaces(rule_name) in rules


def check_connection(settings: QBittorrentSettings) -> str:
    """Verify qBittorrent WebUI access and return the reported version string. Raises QBittorrentError with user-facing guidance when the WebUI is unreachable or authentication fails."""
    client = QBittorrentClient(settings)
    has_credentials = bool(settings.username or settings.password)

    if has_credentials:
        try:
            client.login()
        except QBittorrentError as exc:
            if "HTTP 403" in str(exc):
                raise QBittorrentError(
                    "qBittorrent rejected the login request. Check the WebUI "
                    "username/password in qBittorrent settings and try again."
                ) from exc
            raise
    try:
        return client.get_version()
    except QBittorrentError as exc:
        message = str(exc)
        if not has_credentials and "HTTP 403" in message:
            raise QBittorrentError(
                "qBittorrent WebUI is reachable, but it requires a username and "
                "password. Enter the WebUI credentials from qBittorrent settings "
                "and try again."
            ) from exc
        raise


def submit_rule_draft(
    settings: QBittorrentSettings,
    draft: RuleDraft,
    *,
    add_paused: bool = False,
    assigned_category: str | None = None,
    feed_path: str | None = None
) -> QBittorrentSubmissionResult:
    """Log in, add the RSS feed if needed, create the qBittorrent rule, and verify both were saved. Returns QBittorrentSubmissionResult, or raises QBittorrentError when submission or verification fails."""
    client = QBittorrentClient(settings)
    client.login()

    rule_definition = build_qbittorrent_rule_definition(
        draft,
        add_paused=add_paused,
        assigned_category=assigned_category,
    )
    if not client.has_feed_url(draft.feed_url or ""):
        client.add_feed(
            draft.feed_url or "",
            path=feed_path or build_default_feed_path(draft),
        )
    client.set_auto_downloading_rule(draft.rule_name, rule_definition)
    result = client.verify_rule_draft(draft)
    if not result.verified:
        missing_parts = []
        if not result.feed_verified:
            missing_parts.append("RSS feed")
        if not result.rule_verified:
            missing_parts.append("download rule")
        raise QBittorrentError(
            "qBittorrent submission completed, but verification could not find "
            + " and ".join(missing_parts)
            + "."
        )
    return result
