from __future__ import annotations

from pathlib import Path

from mikancli.cli.prompts import confirm_choice, prompt_password, prompt_text
from mikancli.config import save_config
from mikancli.core.models import AppConfig, QBittorrentSettings, RuleDraft
from mikancli.core.normalize import collapse_spaces, sanitize_folder_name
from mikancli.integrations.qbittorrent import (
    QBittorrentError,
    build_default_feed_path,
    check_connection,
    normalize_qbittorrent_url,
    qbittorrent_rule_exists,
    submit_rule_draft,
)

QBITTORRENT_SETUP_SUCCESS = 0
QBITTORRENT_NOT_CONFIGURED = 1
QBITTORRENT_SUBMISSION_SKIPPED = 2
QBITTORRENT_ERROR = 3


def setup_qbittorrent(config: AppConfig, config_path: Path) -> int:
    """Prompt for qBittorrent WebUI settings, verify the connection, and save them on success. Returns QBITTORRENT_SETUP_SUCCESS when verification succeeds and QBITTORRENT_ERROR when qBittorrent rejects or cannot be reached."""
    print()
    print("----- qBittorrent setup instructions -----")
    print("1. Install qBittorrent and open its settings.")
    print("2. Enable WebUI / remote control if it is not enabled yet.")
    print("3. Copy the WebUI address, username, and password from qBittorrent.")
    print("4. Enter those values below.")
    print("5. After successful verification, the values will be saved to the config file for future runs.")
    print("------------------------------------------")
    print()

    default_url = config.qbittorrent_url or "http://localhost:8080"
    entered_url = (
        collapse_spaces(
            prompt_text(
                "Enter qBittorrent WebUI URL (http://localhost:8080 is the usual default)",
                default=default_url,
                allow_exit=True,
            )
        )
        or "http://localhost:8080"
    )

    print('If you have "Bypass authentication for clients on localhost" enabled in qBittorrent settings, you can just press Enter for the next two prompts.')
    username = (
        collapse_spaces(
            prompt_text(
                "Enter qBittorrent WebUI username (press Enter to leave blank)",
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
        return QBITTORRENT_ERROR

    save_config(
        config_path,
        AppConfig(
            default_save_path=config.default_save_path,
            qbittorrent_url=normalize_qbittorrent_url(entered_url),
            qbittorrent_username=username,
            qbittorrent_password=password,
            qbittorrent_category=config.qbittorrent_category,
            qbittorrent_add_paused=config.qbittorrent_add_paused,
        ),
    )
    print(
        "qBittorrent connection verified successfully "
        f"(version: {version})."
    )
    return QBITTORRENT_SETUP_SUCCESS


def prompt_for_qbittorrent_setup_if_needed(config: AppConfig, config_path: Path) -> int:
    """Offer first-run qBittorrent setup when no WebUI URL is configured. Returns QBITTORRENT_SETUP_SUCCESS when already configured or setup completes, or QBITTORRENT_NOT_CONFIGURED when setup is skipped."""

    if config.qbittorrent_url:
        return QBITTORRENT_SETUP_SUCCESS

    should_setup = confirm_choice(
        "qBittorrent is not set up yet. Set up qBittorrent WebUI now?",
        default=True,
        allow_exit=True,
    )
    if not should_setup:
        return QBITTORRENT_NOT_CONFIGURED

    while True:
        exit_code = setup_qbittorrent(config, config_path)
        if exit_code == QBITTORRENT_SETUP_SUCCESS:
            return QBITTORRENT_SETUP_SUCCESS

        continue_without_setup = confirm_choice(
            "Continue without qBittorrent setup for now?",
            default=False,
            allow_exit=True,
        )
        if continue_without_setup:
            return QBITTORRENT_NOT_CONFIGURED


def run_qbittorrent_configuration_flow(config: AppConfig, config_path: Path) -> int:
    """Run the qBittorrent setup route and allow retrying after failed verification. Returns QBITTORRENT_SETUP_SUCCESS after a successful setup, or QBITTORRENT_NOT_CONFIGURED when the user stops retrying."""

    while True:
        exit_code = setup_qbittorrent(config, config_path)
        if exit_code == QBITTORRENT_SETUP_SUCCESS:
            return QBITTORRENT_SETUP_SUCCESS

        retry_setup = confirm_choice(
            "Retry qBittorrent setup?",
            default=True,
            allow_exit=True,
        )
        if not retry_setup:
            return QBITTORRENT_NOT_CONFIGURED


def prompt_for_rss_feed_name(draft: RuleDraft) -> str:
    """Prompt for the qBittorrent RSS feed path/name, falling back to the default derived from the rule draft."""
    default_feed_path = build_default_feed_path(draft)
    entered = collapse_spaces(
        prompt_text(
            "Enter qBittorrent RSS feed name (press Enter to use the default)",
            default=default_feed_path,
            allow_exit=True,
        )
    )
    return sanitize_folder_name(entered or default_feed_path) or default_feed_path


def prompt_to_submit_rule_to_qbittorrent(config: AppConfig, draft: RuleDraft,) -> int:
    """Ask whether to submit a confirmed rule draft to qBittorrent and report the result. Returns QBITTORRENT_SETUP_SUCCESS on success, QBITTORRENT_NOT_CONFIGURED when no WebUI URL is saved, QBITTORRENT_SUBMISSION_SKIPPED when declined, or QBITTORRENT_ERROR on submission failure."""
    
    if not config.qbittorrent_url:
        return QBITTORRENT_NOT_CONFIGURED

    should_submit = confirm_choice(
        "Submit this RSS feed and download rule to qBittorrent now?",
        default=True,
        allow_exit=True,
    )
    if not should_submit:
        return QBITTORRENT_SUBMISSION_SKIPPED

    settings = QBittorrentSettings(
        url=config.qbittorrent_url,
        username=config.qbittorrent_username,
        password=config.qbittorrent_password,
    )

    try:
        if qbittorrent_rule_exists(settings, draft.rule_name):
            should_replace = confirm_choice(
                f"qBittorrent already has a rule named '{draft.rule_name}'. Replace it?",
                default=False,
                allow_exit=True,
            )
            if not should_replace:
                return QBITTORRENT_SUBMISSION_SKIPPED

        feed_path = prompt_for_rss_feed_name(draft)
        print("Submitting RSS feed and download rule to qBittorrent...")
        submit_rule_draft(
            settings,
            draft,
            add_paused=config.qbittorrent_add_paused,
            assigned_category=config.qbittorrent_category,
            feed_path=feed_path,
        )
    except QBittorrentError as exc:
        print(f"Failed to submit to qBittorrent: {str(exc)}")
        return QBITTORRENT_ERROR

    print("qBittorrent feed and download rule submitted and verified successfully.")
    return QBITTORRENT_SETUP_SUCCESS
