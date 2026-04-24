from __future__ import annotations

from pathlib import Path

from mikancli.cli.prompts import confirm_choice, prompt_password, prompt_text
from mikancli.config import save_config
from mikancli.core.models import AppConfig, QBittorrentSettings
from mikancli.core.normalize import collapse_spaces
from mikancli.integrations.qbittorrent import (
    QBittorrentError,
    check_connection,
    normalize_qbittorrent_url,
)


def _setup_qbittorrent(config: AppConfig, config_path: Path) -> int:
    print()
    print("----- qBittorrent setup instructions -----")
    print("1. Don't forget to have Qbitorrent installed. Once you do, open qBittorrent settings.")
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
                "Enter qBittorrent WebUI URL (http://localhost:8080 is usually the default URL unless you tweeked it in qBittorrent settings)",
                default=default_url,
                allow_exit=True,
            )
        )
        or "http://localhost:8080"
    )

    print()
    print('If you have "Bypass authentication for clients on localhost" enabled in qBittorrent settings, you can just press Enter for the next two prompts.')
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


def _prompt_for_qbittorrent_setup_if_needed(
    config: AppConfig,
    config_path: Path,
) -> int:
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
